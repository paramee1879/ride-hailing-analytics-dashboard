import streamlit as st
import pandas as pd
import geopandas as gpd
import plotly.express as px
import plotly.graph_objects as go
import json
import os, requests, zipfile
from sqlalchemy import create_engine

st.set_page_config(page_title="Ride-Hailing Analytics", layout="wide", page_icon="🚗")

GREEN = "#00C48C"
DARK = "#0E1117"
CARD = "#161B22"
ACCENT2 = "#FFB020"
BLUE = "#4C6FFF"
RED = "#FF5C5C"

st.markdown(f"""
<style>
.stApp {{ background-color: {DARK}; color: #E6E6E6; }}
[data-testid="stMetric"] {{ background-color: {CARD}; border: 1px solid #22282f; border-radius: 12px; padding: 16px; }}
h1, h2, h3 {{ color: {GREEN} !important; }}
</style>
""", unsafe_allow_html=True)

db_url = st.secrets["RAILWAY_URL_PICKME"]
engine = create_engine(db_url.replace("mysql://", "mysql+mysqlconnector://"))

st.title("🚗 Ride-Hailing Analytics Dashboard")
st.caption("Trip volume, revenue, demand patterns and geographic activity")

total_trips = pd.read_sql("SELECT COUNT(*) AS c FROM trips", engine).iloc[0]["c"]
total_revenue = pd.read_sql("SELECT SUM(fare_amount) AS r FROM trips", engine).iloc[0]["r"]
avg_fare = pd.read_sql("SELECT AVG(fare_amount) AS a FROM trips", engine).iloc[0]["a"]
avg_duration = pd.read_sql("SELECT AVG(trip_duration_min) AS d FROM trips", engine).iloc[0]["d"]

c1, c2, c3, c4 = st.columns(4)
c1.metric("Total Trips", f"{total_trips:,}")
c2.metric("Total Revenue", f"${total_revenue:,.0f}")
c3.metric("Avg Fare", f"${avg_fare:,.2f}")
c4.metric("Avg Trip Time", f"{avg_duration:,.1f} min")

st.divider()

tab1, tab2, tab3, tab4 = st.tabs(["📈 Overview", "⏱️ Demand Patterns", "💰 Revenue Analysis", "📍 Zones & Map"])

with tab1:
    revenue_trend = pd.read_sql("SELECT DATE(pickup_datetime) AS day, SUM(fare_amount) AS revenue FROM trips GROUP BY day ORDER BY day", engine)
    fig5 = go.Figure()
    fig5.add_trace(go.Scatter(x=revenue_trend["day"], y=revenue_trend["revenue"], fill='tozeroy', line=dict(color=GREEN, width=3), fillcolor="rgba(0,196,140,0.2)"))
    fig5.update_layout(title="Daily Revenue Trend", plot_bgcolor=CARD, paper_bgcolor=CARD, font_color="#E6E6E6", height=400)
    st.plotly_chart(fig5, use_container_width=True)

    col1, col2 = st.columns(2)
    with col1:
        hourly = pd.read_sql("""
            SELECT CASE WHEN HOUR(pickup_datetime) BETWEEN 6 AND 11 THEN 'Morning'
                WHEN HOUR(pickup_datetime) BETWEEN 12 AND 16 THEN 'Afternoon'
                WHEN HOUR(pickup_datetime) BETWEEN 17 AND 21 THEN 'Evening' ELSE 'Night' END AS period, COUNT(*) AS trips
            FROM trips GROUP BY period
        """, engine)
        fig6 = go.Figure(go.Pie(labels=hourly["period"], values=hourly["trips"], hole=0.55, marker=dict(colors=[GREEN, ACCENT2, BLUE, RED])))
        fig6.update_layout(title="Trips by Time of Day", paper_bgcolor=CARD, font_color="#E6E6E6", height=350)
        st.plotly_chart(fig6, use_container_width=True)
    with col2:
        passengers = pd.read_sql("SELECT passenger_count, COUNT(*) AS trips FROM trips WHERE passenger_count BETWEEN 1 AND 4 GROUP BY passenger_count", engine)
        fig7 = go.Figure(go.Pie(labels=passengers["passenger_count"], values=passengers["trips"], hole=0.55, marker=dict(colors=[GREEN, ACCENT2, BLUE, RED])))
        fig7.update_layout(title="Trips by Passenger Count", paper_bgcolor=CARD, font_color="#E6E6E6", height=350)
        st.plotly_chart(fig7, use_container_width=True)

with tab2:
    hourly_bar = pd.read_sql("SELECT HOUR(pickup_datetime) AS hour, COUNT(*) AS trips FROM trips GROUP BY hour ORDER BY hour", engine)
    fig8 = go.Figure(go.Bar(x=hourly_bar["hour"], y=hourly_bar["trips"], marker_color=GREEN))
    fig8.update_layout(title="Trips by Hour of Day", plot_bgcolor=CARD, paper_bgcolor=CARD, font_color="#E6E6E6", height=380)
    st.plotly_chart(fig8, use_container_width=True)

    daily_bar = pd.read_sql("SELECT DAYNAME(pickup_datetime) AS day, COUNT(*) AS trips FROM trips GROUP BY day", engine)
    fig9 = go.Figure(go.Bar(x=daily_bar["day"], y=daily_bar["trips"], marker_color=ACCENT2))
    fig9.update_layout(title="Trips by Day of Week", plot_bgcolor=CARD, paper_bgcolor=CARD, font_color="#E6E6E6", height=380)
    st.plotly_chart(fig9, use_container_width=True)

    heatmap_data = pd.read_sql("SELECT HOUR(pickup_datetime) AS hour, DAYNAME(pickup_datetime) AS day, COUNT(*) AS trips FROM trips GROUP BY hour, day", engine)
    pivot = heatmap_data.pivot(index="day", columns="hour", values="trips").reindex(["Monday","Tuesday","Wednesday","Thursday","Friday","Saturday","Sunday"])
    fig10 = go.Figure(go.Heatmap(z=pivot.values, x=pivot.columns, y=pivot.index, colorscale="Greens"))
    fig10.update_layout(title="Demand Heatmap: Hour vs Day", paper_bgcolor=CARD, plot_bgcolor=CARD, font_color="#E6E6E6", height=400)
    st.plotly_chart(fig10, use_container_width=True)

with tab3:
    revenue = pd.read_sql("SELECT DATE(pickup_datetime) AS day, SUM(fare_amount) AS revenue, COUNT(*) AS trips FROM trips GROUP BY day ORDER BY day", engine)
    fig11 = go.Figure()
    fig11.add_trace(go.Bar(x=revenue["day"], y=revenue["trips"], name="Trips", marker_color=BLUE, opacity=0.5, yaxis="y2"))
    fig11.add_trace(go.Scatter(x=revenue["day"], y=revenue["revenue"], name="Revenue", line=dict(color=GREEN, width=3)))
    fig11.update_layout(title="Revenue vs Trip Volume", plot_bgcolor=CARD, paper_bgcolor=CARD, font_color="#E6E6E6", height=420,
        yaxis=dict(title="Revenue ($)"), yaxis2=dict(title="Trips", overlaying="y", side="right"))
    st.plotly_chart(fig11, use_container_width=True)

    col1, col2 = st.columns(2)
    with col1:
        scatter_data = pd.read_sql("SELECT trip_distance, fare_amount FROM trips LIMIT 5000", engine)
        fig12 = go.Figure(go.Scatter(x=scatter_data["trip_distance"], y=scatter_data["fare_amount"], mode="markers", marker=dict(color=GREEN, size=4, opacity=0.5)))
        fig12.update_layout(title="Fare vs Trip Distance", xaxis_title="Distance (mi)", yaxis_title="Fare ($)", plot_bgcolor=CARD, paper_bgcolor=CARD, font_color="#E6E6E6", height=380)
        st.plotly_chart(fig12, use_container_width=True)
    with col2:
        fare_dist = pd.read_sql("SELECT fare_amount FROM trips WHERE fare_amount < 100", engine)
        fig13 = go.Figure(go.Histogram(x=fare_dist["fare_amount"], marker_color=ACCENT2, nbinsx=40))
        fig13.update_layout(title="Fare Amount Distribution", plot_bgcolor=CARD, paper_bgcolor=CARD, font_color="#E6E6E6", height=380)
        st.plotly_chart(fig13, use_container_width=True)

    efficiency = pd.read_sql("""
        SELECT ROUND(AVG(fare_amount/trip_distance),2) AS fare_per_mile, ROUND(AVG(fare_amount/trip_duration_min),2) AS fare_per_min
        FROM trips WHERE trip_distance > 0 AND trip_duration_min > 0
    """, engine)
    e1, e2 = st.columns(2)
    e1.metric("Avg Fare per Mile", f"${efficiency.iloc[0]['fare_per_mile']}")
    e2.metric("Avg Fare per Minute", f"${efficiency.iloc[0]['fare_per_min']}")

with tab4:
    col1, col2 = st.columns(2)
    with col1:
        pickup_zones = pd.read_sql("SELECT pickup_zone, COUNT(*) AS trips FROM trips GROUP BY pickup_zone ORDER BY trips DESC LIMIT 15", engine)
        fig14 = go.Figure(go.Bar(x=pickup_zones["trips"], y=pickup_zones["pickup_zone"].astype(str), orientation="h", marker_color=GREEN))
        fig14.update_layout(title="Top 15 Busiest Pickup Zones", plot_bgcolor=CARD, paper_bgcolor=CARD, font_color="#E6E6E6", height=450, yaxis=dict(autorange="reversed"))
        st.plotly_chart(fig14, use_container_width=True)
    with col2:
        dropoff_zones = pd.read_sql("SELECT dropoff_zone, COUNT(*) AS trips FROM trips GROUP BY dropoff_zone ORDER BY trips DESC LIMIT 15", engine)
        fig15 = go.Figure(go.Bar(x=dropoff_zones["trips"], y=dropoff_zones["dropoff_zone"].astype(str), orientation="h", marker_color=ACCENT2))
        fig15.update_layout(title="Top 15 Busiest Dropoff Zones", plot_bgcolor=CARD, paper_bgcolor=CARD, font_color="#E6E6E6", height=450, yaxis=dict(autorange="reversed"))
        st.plotly_chart(fig15, use_container_width=True)

    st.subheader("🗺️ Pickup Demand Map")

    @st.cache_data
    def load_zones():
        if not os.path.exists("taxi_zones/taxi_zones/taxi_zones.shp"):
            url = "https://d37ci6vzurychx.cloudfront.net/misc/taxi_zones.zip"
            r = requests.get(url)
            with open("taxi_zones.zip", "wb") as f:
                f.write(r.content)
            with zipfile.ZipFile("taxi_zones.zip", "r") as z:
                z.extractall("taxi_zones")
        zones_geo = gpd.read_file("taxi_zones/taxi_zones/taxi_zones.shp")
        return zones_geo.to_crs(epsg=4326)

    zones_geo = load_zones()
    zone_counts = pd.read_sql("SELECT pickup_zone AS LocationID, COUNT(*) AS trips FROM trips GROUP BY pickup_zone", engine)
    map_data = zones_geo.merge(zone_counts, on="LocationID", how="left")
    map_data["trips"] = map_data["trips"].fillna(0)

    geojson = json.loads(map_data.to_json())
    fig16 = px.choropleth_mapbox(map_data, geojson=geojson, locations=map_data.index, color="trips",
        color_continuous_scale="Greens", mapbox_style="carto-darkmatter",
        center={"lat": 40.7128, "lon": -74.0060}, zoom=9, opacity=0.7)
    fig16.update_layout(paper_bgcolor=CARD, font_color="#E6E6E6", height=600, margin=dict(l=0, r=0, t=10, b=0))
    st.plotly_chart(fig16, use_container_width=True)
    st.caption("Darker green = higher pickup demand in that zone")
