from census import Census
import pandas as pd

API_KEY = "97c30691a3e9a6ff798aeb0f6edc9244b26dd643"
c = Census (API_KEY)

print("Downloading income data...")

data = c.acs5.state_county_blockgroup(
    fields=("B19013_001E",),  # Median household income
    state_fips="06",
    county_fips="073",
    blockgroup="*",
    year=2022
)

df = pd.DataFrame(data)

df["GEOID"] = (
    df["state"] + df["county"] + df["tract"] + df["block group"]
)

df = df.rename(columns={"B19013_001E": "median_income"})
df = df[["GEOID", "median_income"]]

df.to_csv("san_diego_income.csv", index=False)

print("Income data saved.")
