import streamlit as st
import geopandas as gpd
import pandas as pd
import plotly.express as px
import pydeck as pdk
import osmnx as ox
import numpy as np

st.set_page_config(layout="wide")

# -------------------------------------------------
# LOAD DATA
# -------------------------------------------------

@st.cache_data
def load_data():

    bg = gpd.read_file("processed_block_groups.geojson")
    counties = gpd.read_file("california_counties.geojson")

    san_diego = counties[counties["name"] == "San Diego"]

    bg = bg.to_crs(4326)
    san_diego = san_diego.to_crs(4326)

    return bg, san_diego

bg, san_diego = load_data()

# -------------------------------------------------
# CLEAN DATA
# -------------------------------------------------

bg["median_income"] = pd.to_numeric(bg["median_income"], errors="coerce")
bg = bg[bg["median_income"] > 0]

# -------------------------------------------------
# LOAD HOSPITALS
# -------------------------------------------------

@st.cache_data
def load_hospitals():

    hospitals = ox.features_from_place(
        "San Diego, California, USA",
        tags={"amenity":"hospital"}
    )

    hospitals = hospitals[hospitals.geometry.type=="Point"]
    hospitals = hospitals.to_crs(4326)

    hospitals["lat"] = hospitals.geometry.y
    hospitals["lon"] = hospitals.geometry.x

    return hospitals[["lat","lon"]]

hospitals = load_hospitals()

# -------------------------------------------------
# PREPARE BLOCK GROUP DATA
# -------------------------------------------------

bg["lat"] = bg.geometry.centroid.y
bg["lon"] = bg.geometry.centroid.x

# -------------------------------------------------
# TRAVEL TIME CLASSES
# -------------------------------------------------

bins=[0,10,15,20,100]
labels=["0-10","10-15","15-20",">20"]

bg["travel_class"]=pd.cut(bg["min_travel_time"],bins=bins,labels=labels)

# -------------------------------------------------
# COLOR SCALE
# -------------------------------------------------

def color_scale(x):

    if x=="0-10":
        return [0,200,0]

    elif x=="10-15":
        return [220,220,0]

    elif x=="15-20":
        return [255,140,0]

    else:
        return [200,0,0]

bg["color"]=bg["travel_class"].astype(str).apply(color_scale)

# -------------------------------------------------
# PAGE TITLE
# -------------------------------------------------

st.title("San Diego Healthcare Accessibility Dashboard")

st.caption("Network-based hospital accessibility analysis using OpenStreetMap & US Census")

# -------------------------------------------------
# KPI PANEL
# -------------------------------------------------

total_population = 3282782
hospital_count = 5
coverage_15 = 41.91
access_index = 0.696

k1,k2,k3,k4 = st.columns(4)

k1.metric("Population",f"{total_population:,}")
k2.metric("Hospitals",hospital_count)
k3.metric("15-min Coverage",f"{coverage_15}%")
k4.metric("Accessibility Index",access_index)

# -------------------------------------------------
# MAIN DASHBOARD AREA
# -------------------------------------------------

left,right = st.columns([1.1,2])

# -------------------------------------------------
# LEFT PANEL
# -------------------------------------------------

with left:

    st.subheader("Population by Accessibility")

    travel_counts = bg.groupby("travel_class")["population"].sum().reset_index()

    fig1 = px.bar(
        travel_counts,
        x="travel_class",
        y="population",
        color="travel_class",
        color_discrete_map={
            "0-10":"green",
            "10-15":"yellowgreen",
            "15-20":"orange",
            ">20":"red"
        }
    )

    st.plotly_chart(fig1,use_container_width=True)

    st.subheader("Coverage Metrics")

    metrics_df=pd.DataFrame({
        "Travel Time":[10,15,20],
        "Coverage":[34.27,41.91,45.56]
    })

    fig2 = px.line(
        metrics_df,
        x="Travel Time",
        y="Coverage",
        markers=True
    )

    st.plotly_chart(fig2,use_container_width=True)

# -------------------------------------------------
# MAP PANEL
# -------------------------------------------------

with right:

    st.subheader("Accessibility Map")

    map_df = pd.DataFrame(bg.drop(columns="geometry"))

    population_layer = pdk.Layer(
        "ScatterplotLayer",
        map_df,
        get_position='[lon,lat]',
        get_color='color',
        get_radius=120,
        pickable=True
    )

    hospital_layer = pdk.Layer(
        "ScatterplotLayer",
        hospitals,
        get_position='[lon,lat]',
        get_color=[255,0,0],
        get_radius=300
    )

    boundary_layer = pdk.Layer(
        "GeoJsonLayer",
        san_diego.__geo_interface__,
        stroked=True,
        filled=False,
        get_line_color=[255,255,255],
        line_width_min_pixels=2
    )

    view_state=pdk.ViewState(
        latitude=32.8,
        longitude=-117.1,
        zoom=9
    )

    deck=pdk.Deck(
        layers=[boundary_layer,population_layer,hospital_layer],
        initial_view_state=view_state,
        tooltip={"text":"Travel Time: {min_travel_time} min\nPopulation: {population}"}
    )

    st.pydeck_chart(deck)

# -------------------------------------------------
# EQUITY ANALYSIS
# -------------------------------------------------

st.markdown("---")
st.subheader("Equity Analysis")

bg["income_group"]=pd.qcut(
    bg["median_income"],
    4,
    labels=["Low","Lower-Middle","Upper-Middle","High"],
    duplicates="drop"
)

e1,e2 = st.columns(2)

with e1:

    fig3 = px.box(
        bg,
        x="income_group",
        y="min_travel_time",
        color="income_group",
        title="Travel Time Distribution by Income Group"
    )

    st.plotly_chart(fig3,use_container_width=True)

with e2:

    underserved = bg[bg["min_travel_time"]>20]

    underserved_df = underserved.groupby("income_group")["population"].sum().reset_index()

    fig4 = px.bar(
        underserved_df,
        x="income_group",
        y="population",
        color="income_group",
        title="Population with >20 min Travel Time"
    )

    st.plotly_chart(fig4,use_container_width=True)


# -------------------------------------------------
# INEQUALITY METRICS
# -------------------------------------------------

i1,i2,i3 = st.columns(3)

i1.metric("Population >20 min travel","505,709")
i2.metric("Vulnerable population","113,782")
i3.metric("Gini coefficient","0.182")

st.caption("GIS Network Accessibility Model | San Diego County")