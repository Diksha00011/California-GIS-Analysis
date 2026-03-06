import geopandas as gpd
import osmnx as ox
import matplotlib.pyplot as plt
import pandas as pd

# -------------------------------
# 1️⃣ Study Area
# -------------------------------

place_name = "San Diego, California, USA"

san_diego = ox.geocode_to_gdf(place_name)

# -------------------------------
# 2️⃣ Download Hospitals
# -------------------------------

tags = {"amenity": "hospital"}
hospitals = ox.features_from_place(place_name, tags)
hospitals = hospitals[hospitals.geometry.type == "Point"]

# Reproject
san_diego = san_diego.to_crs(epsg=3857)
hospitals = hospitals.to_crs(epsg=3857)

# -------------------------------
# 3️⃣ 5km Buffer
# -------------------------------

buffer_distance = 5000
hospitals["geometry"] = hospitals.geometry.buffer(buffer_distance)
access_area = hospitals.dissolve()

# -------------------------------
# 4️⃣ Load Block Groups
# -------------------------------

bg = gpd.read_file("tl_2022_06_bg/tl_2022_06_bg.shp")
bg = bg[bg["COUNTYFP"] == "073"]
bg = bg.to_crs(epsg=3857)

print("Block groups loaded:", len(bg))

# -------------------------------
# 5️⃣ Load ACS CSV
# -------------------------------

pop = pd.read_csv("san_diego_population.csv")

# Convert to string
bg["GEOID"] = bg["GEOID"].astype(str)
pop["GEOID"] = pop["GEOID"].astype(str)

# Add missing leading zero to CSV GEOID (make length 12)
pop["GEOID"] = pop["GEOID"].str.zfill(12)

print("BG GEOID length:", bg["GEOID"].str.len().unique())
print("POP GEOID length:", pop["GEOID"].str.len().unique())

# Merge
bg = bg.merge(pop, on="GEOID", how="left")
# -------------------------------
# 6️⃣ Coverage Calculation
# -------------------------------

bg["covered"] = bg.geometry.intersects(access_area.geometry.iloc[0])

total_population = bg["population"].sum()
covered_population = bg.loc[bg["covered"], "population"].sum()

coverage_percent = (covered_population / total_population) * 100

print(f"Total population: {int(total_population):,}")
print(f"Covered population: {int(covered_population):,}")
print(f"Real population coverage: {coverage_percent:.2f}%")

# -------------------------------
# 7️⃣ Visualization
# -------------------------------

fig, ax = plt.subplots(figsize=(8, 8))

bg.plot(ax=ax, column="covered", cmap="coolwarm", legend=True)
access_area.plot(ax=ax, color="none", edgecolor="black")

plt.title("Population Coverage - Hospital Accessibility (5km)")
plt.show()