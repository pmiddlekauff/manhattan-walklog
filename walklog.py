import pandas as pd
import folium
import math
import os

# 1. Pull the live data directly from your Google Sheet
SHEET_CSV_URL = "https://docs.google.com/spreadsheets/d/1eTzd_iG590gVdbu6q7p0iDElsCVLr9QTSP1wRWagozg/export?format=csv&gid=1407515623"

print("Fetching data from Google Sheets...")
try:
    df = pd.read_csv(SHEET_CSV_URL)
    df.columns = df.columns.str.strip()
    print(f"Successfully loaded {len(df)} rows.")
except Exception as e:
    print(f"FAILED to load CSV: {e}")
    exit(1)

# 2. THE TIMESTAMP GATE
latest_timestamp = str(df['Timestamp'].iloc[-1])
cache_file = 'last_run.txt'

if os.path.exists(cache_file):
    with open(cache_file, 'r') as f:
        last_timestamp = f.read().strip()
    if latest_timestamp == last_timestamp:
        print(f"No new walks logged since {last_timestamp}. Exiting.")
        exit(0)

# 3. DATA CLEANING
df = df.fillna("")
geo_cols = ["Start Lat", "Start Lon", "End Lat", "End Lon"]
for col in geo_cols:
    df[col] = pd.to_numeric(df[col], errors='coerce')

df = df.dropna(subset=geo_cols)

if df.empty:
    print("CRITICAL ERROR: No valid coordinates found in Columns M-P.")
    exit(1)

# 4. MAP GENERATION
side_col = "Side of Street" if "Side of Street" in df.columns else "Side"
dir_col = "Direction"

pts = df[["Start Lat","Start Lon"]].values.tolist() + df[["End Lat","End Lon"]].values.tolist()
min_lat, max_lat = min(p[0] for p in pts), max(p[0] for p in pts)
min_lon, max_lon = min(p[1] for p in pts), max(p[1] for p in pts)
center = [(min_lat+max_lat)/2, (min_lon+max_lon)/2]

def bearing_deg(lat1, lon1, lat2, lon2):
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dlon = math.radians(lon2 - lon1)
    y = math.sin(dlon) * math.cos(phi2)
    x = math.cos(phi1)*math.sin(phi2) - math.sin(phi1)*math.cos(phi2)*math.cos(dlon)
    return (math.degrees(math.atan2(y, x)) + 360) % 360

m = folium.Map(location=center, zoom_start=15, tiles="OpenStreetMap")
side_colors = {"N":"blue","S":"red","E":"green","W":"purple","BOTH":"orange","UNKNOWN":"gray"}

for _, row in df.iterrows():
    start, end = (float(row["Start Lat"]), float(row["Start Lon"])), (float(row["End Lat"]), float(row["End Lon"]))
    color = side_colors.get(str(row.get(side_col, "UNKNOWN")).strip().upper(), "black")
    
    popup_text = f"<b>{row['Street Name']}</b><br>Side: {row.get(side_col, 'N/A')}"
    folium.PolyLine([start, end], weight=6, color=color, popup=popup_text).add_to(m)

m.fit_bounds([[min_lat, min_lon], [max_lat, max_lon]])
m.save("manhattan_walklog_map.html")

# Update cache
with open(cache_file, 'w') as f:
    f.write(latest_timestamp)

print("Map updated successfully!")
