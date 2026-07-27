import streamlit as st
import pandas as pd
import geopandas as gpd
import plotly.express as px
import plotly.graph_objects as go
import json
import os, requests, zipfile
from sqlalchemy import create_engine

# ============================================================
# DESIGN TOKENS — professional light theme
# ============================================================
st.set_page_config(page_title="Ride-Hailing Analytics", layout="wide", page_icon="🚕")

BG = "#F6F8FB"
CARD = "#FFFFFF"
BORDER = "#E5E9F0"
INK = "#1F2937"
MUTED = "#6B7280"
NAVY = "#1F2A44"
TEAL = "#0F9D8E"
AMBER = "#F5A623"
CORAL = "#EF5B5B"
INDIGO = "#5B6EF5"
PALETTE = [TEAL, AMBER, INDIGO, CORAL]

st.markdown(f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');
html, body, [class*="css"] {{ font-family: 'Inter', sans-serif; }}
.stApp {{ background-color: {BG}; }}

[data-testid="stMetric"] {{
    background-color: {CARD};
    border: 1px solid {BORDER};
    border-radius: 14px;
    padding: 16px 18px;
    box-shadow: 0 1px 3px rgba(16, 24, 40, 0.04);
}}
[data-testid="stMetricLabel"] {{ color: {MUTED} !important; font-weight: 500; }}
[data-testid="stMetricValue"] {{ color: {NAVY} !important; font-weight: 700; }}

h1 {{ color: {NAVY} !important; font-weight: 800 !important; letter-spacing: -0.02em; }}
h2, h3, h4 {{ color: {NAVY} !important; font-weight: 700 !important; }}

div[data-testid="stPlotlyChart"] {{
    background-color: {CARD};
    border: 1px solid {BORDER};
    border-radius: 14px;
    padding: 10px 8px 4px 8px;
    box-shadow: 0 1px 3px rgba(16, 24, 40, 0.04);
}}

.section-label {{
    color: {MUTED}; font-size: 12px; font-weight: 700;
    text-transform: uppercase; letter-spacing: 0.06em;
    margin: 18px 0 4px 2px;
}}
.dashboard-subtitle {{ color: {MUTED}; font-size: 15px; margin-top: -8px; }}
hr {{ border-color: {BORDER} !important; margin: 8px 0 !important; }}
</style>
""", unsafe_allow_html=True)


def style_fig(fig, title, height=320, showlegend=False):
    fig.update_layout(
        title=dict(text=title, font=dict(size=15, color=NAVY, family="Inter"), x=0.02, xanchor="left"),
        plot_bgcolor=CARD, paper_bgcolor=CARD,
        font=dict(color=INK, family="Inter", size=11),
        height=height, showlegend=showlegend,
        margin=dict(l=10, r=10, t=45, b=10),
        xaxis=dict(gridcolor=BORDER, zeroline=False),
        yaxis=dict(gridcolor=BORDER, zeroline=False),
    )
    return fig


# ============================================================
# DATA CONNECTION
# ============================================================
db_url = st.secrets["RAILWAY_URL_PICKME"]
engine = create_engine(db_url.replace("mysql://", "mysql+mysqlconnector://"))

st.title("🚕 Ride-Hailing Analytics")
st.markdown('<p class="dashboard-subtitle">Trip volume, revenue, demand patterns and geographic activity — full report</p>', unsafe_allow_html=True)

# ---------------- KPI ROW ----------------
total_trips = pd.read_sql("SELECT COUNT(*) AS c FROM trips", engine).iloc[0]["c"]
total_revenue = pd.read_sql("SELECT SUM(fare_amount) AS r FROM trips", engine).iloc[0]["r"]
avg_fare = pd.read_sql("SELECT AVG(fare_amount) AS a FROM trips", engine).iloc[0]["a"]
avg_duration = pd.read_sql("SELECT AVG(trip_duration_min) AS d FROM trips", engine).iloc[0]["d"]

k1, k2, k3, k4 = st.columns(4)
k1.metric("Total Trips", f"{total_trips:,}")
k2.metric("Total Revenue", f"${total_revenue:,.0f}")
k3.metric("Avg Fare", f"${avg_fare:,.2f}")
k4.metric("Avg Trip Time", f"{avg_duration:,.1f} min")

# ============================================================
# ROW 1 — Revenue trend + 2 donuts
# ============================================================
st.markdown('<div class="section-label">Revenue & Trip Mix</div>', unsafe_allow_html=True)
r1c1, r1c2, r1c3 = st.columns([2, 1, 1])

with r1c1:
    revenue_trend = pd.read_sql("SELECT DATE(pickup_datetime) AS day, SUM(fare_amount) AS revenue FROM trips GROUP BY day ORDER BY day", engine)
    fig1 = go.Figure(go.Scatter(x=revenue_trend["day"], y=revenue_trend["revenue"], fill='tozeroy',
        line=dict(color=TEAL, width=3), fillcolor="rgba(15,157,142,0.12)"))
    st.plotly_chart(style_fig(fig1, "Daily Revenue Trend", height=300), use_container_width=True)

with r1c2:
    hourly = pd.read_sql("""
        SELECT CASE WHEN HOUR(pickup_datetime) BETWEEN 6 AND 11 THEN 'Morning'
            WHEN HOUR(pickup_datetime) BETWEEN 12 AND 16 THEN 'Afternoon'
            WHEN HOUR(pickup_datetime) BETWEEN 17 AND 21 THEN 'Evening' ELSE 'Night' END AS period, COUNT(*) AS trips
        FROM trips GROUP BY period
    """, engine)
    fig2 = go.Figure(go.Pie(labels=hourly["period"], values=hourly["trips"], hole=0.6, marker=dict(colors=PALETTE)))
    st.plotly_chart(style_fig(fig2, "Time of Day", height=300, showlegend=True), use_container_width=True)

with r1c3:
    passengers = pd.read_sql("SELECT passenger_count, COUNT(*) AS trips FROM trips WHERE passenger_count BETWEEN 1 AND 4 GROUP BY passenger_count", engine)
    fig3 = go.Figure(go.Pie(labels=passengers["passenger_count"], values=passengers["trips"], hole=0.6, marker=dict(colors=PALETTE)))
    st.plotly_chart(style_fig(fig3, "Passenger Count", height=300, showlegend=True), use_container_width=True)

# ============================================================
# ROW 2 — Hourly / Daily / Heatmap
# ============================================================
st.markdown('<div class="section-label">Demand Patterns</div>', unsafe_allow_html=True)
r2c1, r2c2 = st.columns(2)

with r2c1:
    hourly_bar = pd.read_sql("SELECT HOUR(pickup_datetime) AS hour, COUNT(*) AS trips FROM trips GROUP BY hour ORDER BY hour", engine)
    fig4 = go.Figure(go.Bar(x=hourly_bar["hour"], y=hourly_bar["trips"], marker_color=TEAL))
    st.plotly_chart(style_fig(fig4, "Trips by Hour of Day", height=280), use_container_width=True)

with r2c2:
    daily_bar = pd.read_sql("SELECT DAYNAME(pickup_datetime) AS day, COUNT(*) AS trips FROM trips GROUP BY day", engine)
    fig5 = go.Figure(go.Bar(x=daily_bar["day"], y=daily_bar["trips"], marker_color=AMBER))
    st.plotly_chart(style_fig(fig5, "Trips by Day of Week", height=280), use_container_width=True)

heatmap_data = pd.read_sql("SELECT HOUR(pickup_datetime) AS hour, DAYNAME(pickup_datetime) AS day, COUNT(*) AS trips FROM trips GROUP BY hour, day", engine)
pivot = heatmap_data.pivot(index="day", columns="hour", values="trips").reindex(
    ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"])
fig6 = go.Figure(go.Heatmap(z=pivot.values, x=pivot.columns, y=pivot.index, colorscale="Teal"))
st.plotly_chart(style_fig(fig6, "Demand Heatmap: Hour vs Day", height=300), use_container_width=True)

# ============================================================
# ROW 3 — Revenue vs Volume, Scatter, Histogram
# ============================================================
st.markdown('<div class="section-label">Revenue Analysis</div>', unsafe_allow_html=True)

revenue = pd.read_sql("SELECT DATE(pickup_datetime) AS day, SUM(fare_amount) AS revenue, COUNT(*) AS trips FROM trips GROUP BY day ORDER BY day", engine)
fig7 = go.Figure()
fig7.add_trace(go.Bar(x=revenue["day"], y=revenue["trips"], name="Trips", marker_color=INDIGO, opacity=0.35, yaxis="y2"))
fig7.add_trace(go.Scatter(x=revenue["day"], y=revenue["revenue"], name="Revenue", line=dict(color=TEAL, width=3)))
fig7 = style_fig(fig7, "Revenue vs Trip Volume", height=300, showlegend=True)
fig7.update_layout(yaxis=dict(title="Revenue ($)", gridcolor=BORDER), yaxis2=dict(title="Trips", overlaying="y", side="right", showgrid=False))
st.plotly_chart(fig7, use_container_width=True)

r3c1, r3c2 = st.columns(2)
with r3c1:
    scatter_data = pd.read_sql("SELECT trip_distance, fare_amount FROM trips LIMIT 5000", engine)
    fig8 = go.Figure(go.Scatter(x=scatter_data["trip_distance"], y=scatter_data["fare_amount"], mode="markers",
        marker=dict(color=TEAL, size=5, opacity=0.45)))
    fig8 = style_fig(fig8, "Fare vs Trip Distance", height=300)
    fig8.update_layout(xaxis_title="Distance (mi)", yaxis_title="Fare ($)")
    st.plotly_chart(fig8, use_container_width=True)
with r3c2:
    fare_dist = pd.read_sql("SELECT fare_amount FROM trips WHERE fare_amount < 100", engine)
    fig9 = go.Figure(go.Histogram(x=fare_dist["fare_amount"], marker_color=AMBER, nbinsx=40))
    st.plotly_chart(style_fig(fig9, "Fare Amount Distribution", height=300), use_container_width=True)

efficiency = pd.read_sql("""
    SELECT ROUND(AVG(fare_amount/trip_distance),2) AS fare_per_mile, ROUND(AVG(fare_amount/trip_duration_min),2) AS fare_per_min
    FROM trips WHERE trip_distance > 0 AND trip_duration_min > 0
""", engine)
e1, e2 = st.columns(2)
e1.metric("Avg Fare per Mile", f"${efficiency.iloc[0]['fare_per_mile']}")
e2.metric("Avg Fare per Minute", f"${efficiency.iloc[0]['fare_per_min']}")

# ============================================================
# ROW 4 — Zones + Map
# ============================================================
st.markdown('<div class="section-label">Zones & Geographic Activity</div>', unsafe_allow_html=True)

r4c1, r4c2 = st.columns(2)
with r4c1:
    pickup_zones = pd.read_sql("SELECT pickup_zone, COUNT(*) AS trips FROM trips GROUP BY pickup_zone ORDER BY trips DESC LIMIT 15", engine)
    fig10 = go.Figure(go.Bar(x=pickup_zones["trips"], y=pickup_zones["pickup_zone"].astype(str), orientation="h", marker_color=TEAL))
    fig10 = style_fig(fig10, "Top 15 Busiest Pickup Zones", height=380)
    fig10.update_layout(yaxis=dict(autorange="reversed", gridcolor=BORDER))
    st.plotly_chart(fig10, use_container_width=True)
with r4c2:
    dropoff_zones = pd.read_sql("SELECT dropoff_zone, COUNT(*) AS trips FROM trips GROUP BY dropoff_zone ORDER BY trips DESC LIMIT 15", engine)
    fig11 = go.Figure(go.Bar(x=dropoff_zones["trips"], y=dropoff_zones["dropoff_zone"].astype(str), orientation="h", marker_color=AMBER))
    fig11 = style_fig(fig11, "Top 15 Busiest Dropoff Zones", height=380)
    fig11.update_layout(yaxis=dict(autorange="reversed", gridcolor=BORDER))
    st.plotly_chart(fig11, use_container_width=True)

st.markdown('<div class="section-label">Pickup Demand Map</div>', unsafe_allow_html=True)

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
fig12 = px.choropleth_mapbox(
    map_data, geojson=geojson, locations=map_data.index, color="trips",
    color_continuous_scale="Teal", mapbox_style="carto-positron",
    center={"lat": 40.7128, "lon": -74.0060}, zoom=9, opacity=0.75
)
fig12.update_layout(paper_bgcolor=CARD, font_color=INK, height=520, margin=dict(l=0, r=0, t=10, b=0))
st.plotly_chart(fig12, use_container_width=True)
st.caption("Darker teal = higher pickup demand in that zone")
