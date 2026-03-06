import osmnx as ox
import geopandas as gpd
import matplotlib.pyplot as plt

# Define study area
place_name = "San Diego, California, USA"

# Get San Diego boundary
san_diego = ox.geocode_to_gdf(place_name)

# Download hospitals from OSM
tags = {"amenity": "hospital"}
hospitals = ox.features_from_place(place_name, tags)

# Keep only point geometries
hospitals = hospitals[hospitals.geometry.type == "Point"]

print("Hospitals downloaded:", len(hospitals))

# Reproject to metric CRS for buffering
san_diego = san_diego.to_crs(epsg=3857)
hospitals = hospitals.to_crs(epsg=3857)

# Create 5 km buffer around hospitals
buffer_distance = 5000  # meters
hospitals["geometry"] = hospitals.geometry.buffer(buffer_distance)

# Dissolve all buffers into one area
access_area = hospitals.dissolve()

# Plot
fig, ax = plt.subplots(figsize=(8,8))

san_diego.plot(ax=ax, color="lightgray", edgecolor="black")
access_area.plot(ax=ax, color="red", alpha=0.5)

plt.title("5 km Hospital Accessibility - San Diego")
plt.show()

# Calculate area coverage
san_diego["area_m2"] = san_diego.geometry.area
access_area["area_m2"] = access_area.geometry.area

coverage_percent = (access_area["area_m2"].values[0] / san_diego["area_m2"].values[0]) * 100

print(f"Hospital coverage: {coverage_percent:.2f}% of San Diego area")
access_area.to_file("hospital_access_5km.geojson", driver="GeoJSON")