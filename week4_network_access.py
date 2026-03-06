import geopandas as gpd
import osmnx as ox
import networkx as nx
import pandas as pd
import matplotlib.pyplot as plt
from shapely.geometry import Point

# ----------------------------------
# 1️⃣ Study Area
# ----------------------------------

place_name = "San Diego, California, USA"

print("Downloading road network...")
G = ox.graph_from_place(place_name, network_type="drive")

# Add travel time (in seconds)
G = ox.add_edge_speeds(G)
G = ox.add_edge_travel_times(G)

# ----------------------------------
# 2️⃣ Download Hospitals
# ----------------------------------

print("Downloading hospitals...")
tags = {"amenity": "hospital"}
hospitals = ox.features_from_place(place_name, tags)
hospitals = hospitals[hospitals.geometry.type == "Point"]

# ----------------------------------
# 3️⃣ Create 15-Minute Isochrones
# ----------------------------------

isochrones = []

travel_time_minutes = 15
travel_time_seconds = travel_time_minutes * 60

for idx, row in hospitals.iterrows():

    hospital_point = row.geometry
    nearest_node = ox.nearest_nodes(G, hospital_point.x, hospital_point.y)

    subgraph = nx.ego_graph(
        G,
        nearest_node,
        radius=travel_time_seconds,
        distance="travel_time"
    )

    nodes = ox.graph_to_gdfs(subgraph, edges=False)

    polygon = nodes.unary_union.convex_hull
    isochrones.append(polygon)

print("Isochrones created.")

# Combine all hospital service areas
iso_gdf = gpd.GeoDataFrame(geometry=isochrones, crs="EPSG:4326")
iso_union = iso_gdf.dissolve()

# ----------------------------------
# 4️⃣ Load Block Groups
# ----------------------------------

bg = gpd.read_file("tl_2022_06_bg/tl_2022_06_bg.shp")
bg = bg[bg["COUNTYFP"] == "073"]

# Reproject to match isochrone CRS
bg = bg.to_crs(iso_union.crs)

print("Block groups loaded:", len(bg))

# ----------------------------------
# 5️⃣ Load Population
# ----------------------------------

pop = pd.read_csv("san_diego_population.csv")
pop["GEOID"] = pop["GEOID"].astype(str).str.zfill(12)
bg["GEOID"] = bg["GEOID"].astype(str)

bg = bg.merge(pop, on="GEOID", how="left")
bg["population"] = bg["population"].fillna(0)

# ----------------------------------
# 6️⃣ Calculate Coverage
# ----------------------------------

bg["covered"] = bg.geometry.intersects(iso_union.geometry.iloc[0])

total_population = bg["population"].sum()
covered_population = bg.loc[bg["covered"], "population"].sum()

coverage_percent = (covered_population / total_population) * 100

print(f"\nTotal population: {int(total_population):,}")
print(f"Covered population (15-min drive): {int(covered_population):,}")
print(f"Coverage percentage: {coverage_percent:.2f}%")

# ----------------------------------
# 7️⃣ Visualization
# ----------------------------------

fig, ax = plt.subplots(figsize=(8, 8))

bg.plot(ax=ax, column="covered", cmap="coolwarm", legend=True)
iso_union.plot(ax=ax, color="none", edgecolor="black")

plt.title("15-Minute Drive-Time Hospital Accessibility")
plt.show()