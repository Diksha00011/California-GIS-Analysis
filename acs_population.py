from census import Census
import pandas as pd

# 🔐 Replace with your NEW Census API key
CENSUS_KEY = "97c30691a3e9a6ff798aeb0f6edc9244b26dd643"

# Connect to Census API
c = Census(CENSUS_KEY)

print("Connecting to Census API...")

# Download ACS 5-Year Estimate population
acs_data = c.acs5.state_county_blockgroup(
    fields=('B01003_001E',),   # Total population
    state_fips='06',           # California
    county_fips='073',         # San Diego County
    blockgroup='*'
)

print("Download successful!")

# Convert to DataFrame
df = pd.DataFrame(acs_data)

# Rename population column
df.rename(columns={"B01003_001E": "population"}, inplace=True)

# Convert all columns to string to preserve leading zeros
df = df.astype(str)

# Create full GEOID (12-digit block group identifier)
df["GEOID"] = (
    df["state"].str.zfill(2) +
    df["county"].str.zfill(3) +
    df["tract"].str.zfill(6) +
    df["block group"].str.zfill(1)
)

# Keep only necessary columns
df = df[["GEOID", "population"]]

# Convert population back to numeric
df["population"] = pd.to_numeric(df["population"], errors="coerce")

# Save to CSV
df.to_csv("san_diego_population.csv", index=False)

print("ACS population data saved as san_diego_population.csv")
print("Total records downloaded:", len(df))
