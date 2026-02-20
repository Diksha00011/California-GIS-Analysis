# California-GIS-Analysis
Urban Accessibility &amp; Exposure Dashboard: A spatial data pipeline that measures accessibility to key services (hospitals, schools, transit) and maps population exposure to hazards (flood zones / heat islands), with an interactive web map and an API-backed data summary.

Part 1:
Installed and configured Python, VS Code, and virtual environment
Set up GeoPandas, OSMnx, Matplotlib, and Pandas libraries
Loaded California county GeoJSON dataset
Filtered San Diego County using attribute query
Reprojected data for accurate spatial measurements
Created first GIS visualization using GeoPandas

Part 2:
Downloaded hospital locations using OpenStreetMap (OSMnx)
Extracted hospital point geometries within San Diego
Reprojected datasets to projected CRS (EPSG:3857)
Generated 5 km buffer zones around hospitals
Dissolved buffers to create unified service area
Visualized hospital accessibility coverage map

Part 3:
Downloaded San Diego Census Block Groups (TIGER 2022)
Retrieved official ACS population using Census API
Cleaned and standardized GEOID fields
Joined population data to spatial geometries
Created 5 km hospital accessibility buffer
Calculated real population coverage percentage
Estimated 22.66% of population lives within 5 km of hospital

