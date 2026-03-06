import geopandas as gpd
import osmnx as ox
import networkx as nx
import pandas as pd
import numpy as np
import os
from census import Census

# ======================================
# 1️⃣ Study Area
# ======================================

place_name = "San Diego, California, USA"

print("Downloading road network...")
G = ox.graph_from_place(place_name, network_type="drive")
G = ox.project_graph(G)
G = ox.add_edge_speeds(G)
G = ox.add_edge_travel_times(G)

# ======================================
# 2️⃣ Download Hospitals
# ======================================

print("Downloading hospitals...")
tags = {"amenity": "hospital"}
hospitals = ox.features_from_place(place_name, tags)
hospitals = hospitals[hospitals.geometry.type == "Point"]
hospitals = hospitals.to_crs(G.graph["crs"])

print("Hospitals found:", len(hospitals))

# Precompute hospital nodes
hospital_nodes = [
    ox.distance.nearest_nodes(G, row.geometry.x, row.geometry.y)
    for _, row in hospitals.iterrows()
]

# ======================================
# 3️⃣ Load Block Groups
# ======================================

bg = gpd.read_file("tl_2022_06_bg/tl_2022_06_bg.shp")
bg = bg[bg["COUNTYFP"] == "073"]
bg = bg.to_crs(G.graph["crs"])

print("Block groups loaded:", len(bg))

# ======================================
# 4️⃣ Load Population
# ======================================

pop = pd.read_csv("san_diego_population.csv")
pop["GEOID"] = pop["GEOID"].astype(str).str.zfill(12)
bg["GEOID"] = bg["GEOID"].astype(str).str.zfill(12)

bg = bg.merge(pop, on="GEOID", how="left")
bg["population"] = bg["population"].fillna(0)

# ======================================
# 5️⃣ Multi-Threshold Coverage
# ======================================

travel_times = [10, 15, 20]
results = {}

for t in travel_times:
    print(f"\nCalculating {t}-minute coverage...")

    travel_seconds = t * 60
    isochrones = []

    for hospital_node in hospital_nodes:

        subgraph = nx.ego_graph(
            G,
            hospital_node,
            radius=travel_seconds,
            distance="travel_time"
        )

        nodes = ox.graph_to_gdfs(subgraph, edges=False)

        # Updated union method
        polygon = nodes.geometry.union_all().convex_hull
        isochrones.append(polygon)

    iso_gdf = gpd.GeoDataFrame(geometry=isochrones, crs=G.graph["crs"])
    iso_union = iso_gdf.dissolve()

    bg[f"covered_{t}"] = bg.geometry.intersects(iso_union.geometry.iloc[0])

    covered_pop = bg.loc[bg[f"covered_{t}"], "population"].sum()
    total_pop = bg["population"].sum()

    results[t] = (covered_pop / total_pop) * 100

print("\n===== Coverage Comparison =====")
for t, val in results.items():
    print(f"{t}-minute coverage: {val:.2f}%")

# ======================================
# 6️⃣ Minimum Travel Time
# ======================================

print("\nCalculating minimum travel time...")

bg["min_travel_time"] = np.nan

for i, row in bg.iterrows():

    centroid = row.geometry.centroid
    bg_node = ox.distance.nearest_nodes(G, centroid.x, centroid.y)

    min_time = float("inf")

    for hospital_node in hospital_nodes:
        try:
            travel_time = nx.shortest_path_length(
                G,
                bg_node,
                hospital_node,
                weight="travel_time"
            )
            if travel_time < min_time:
                min_time = travel_time
        except:
            continue

    bg.at[i, "min_travel_time"] = min_time / 60

# Clean infinities
bg["min_travel_time"] = bg["min_travel_time"].replace(
    [np.inf, -np.inf], np.nan
)

valid_bg = bg.dropna(subset=["min_travel_time"]).copy()

# ======================================
# Accessibility Index
# ======================================

max_time = valid_bg["min_travel_time"].max()
valid_bg["access_index"] = 1 - (valid_bg["min_travel_time"] / max_time)

bg["access_index"] = valid_bg["access_index"]

weighted_score = (
    (valid_bg["access_index"] * valid_bg["population"]).sum()
    / valid_bg["population"].sum()
)

print(f"\nPopulation-weighted accessibility score: {weighted_score:.3f}")

# ======================================
# Equity Analysis
# ======================================

print("\nRunning equity analysis...")

income_file = "san_diego_income.csv"

if not os.path.exists(income_file):

    print("Downloading income data from Census API...")

    API_KEY = "97c30691a3e9a6ff798aeb0f6edc9244b26dd643"
    c = Census(API_KEY)

    income_data = c.acs5.state_county_blockgroup(
        fields=("B19013_001E",),
        state_fips="06",
        county_fips="073",
        blockgroup="*",
        year=2022
    )

    income_df = pd.DataFrame(income_data)

    income_df["GEOID"] = (
        income_df["state"] +
        income_df["county"] +
        income_df["tract"] +
        income_df["block group"]
    )

    income_df = income_df.rename(
        columns={"B19013_001E": "median_income"}
    )

    income_df = income_df[["GEOID", "median_income"]]
    income_df.to_csv(income_file, index=False)

    print("Income data saved.")

income = pd.read_csv(income_file)
income["GEOID"] = income["GEOID"].astype(str).str.zfill(12)

bg = bg.merge(income, on="GEOID", how="left")

# Correlation
correlation = bg[["median_income", "min_travel_time"]].corr().iloc[0, 1]
print(f"Income vs Travel Time Correlation: {correlation:.3f}")

# Vulnerable Population
income_threshold = bg["median_income"].quantile(0.25)

vulnerable = bg[
    (bg["median_income"] < income_threshold) &
    (bg["min_travel_time"] > 20)
]

print("Vulnerable population:",
      int(vulnerable["population"].sum()))

# ======================================
# Gini Coefficient
# ======================================

x = valid_bg["access_index"].values

if len(x) > 0 and np.sum(x) != 0:
    x = np.sort(x)
    n = len(x)
    gini = (2 * np.sum((np.arange(1, n+1) * x))) / \
           (n * np.sum(x)) - (n + 1)/n
    print(f"Gini coefficient: {gini:.3f}")
else:
    print("Gini could not be calculated.")

# ======================================
# SAVE FILE SAFELY
# ======================================

script_dir = os.path.dirname(os.path.abspath(__file__))
output_path = os.path.join(script_dir, "processed_block_groups.geojson")

bg.to_file(output_path, driver="GeoJSON")

print("\nProcessed GeoJSON saved to:")
print(output_path)