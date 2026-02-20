import pandas as pd
import folium
import requests
import time
import os

# 1. SETTINGS & URL
SHEET_CSV_URL = "https://docs.google.com/spreadsheets/d/1eTzd_iG590gVdbu6q7p0iDElsCVLr9QTSP1wRWagozg/export?format=csv&gid=1407515623"

print("--- STARTING MANHATTAN WALKLOG UPDATE (WITH STREET SNAPPING) ---")

# 2. FETCH DATA
try:
    df = pd.read_csv(SHEET_CSV_URL)
    df.columns = df.columns.str.strip()
    print(f"Successfully loaded {len(df)} rows from Google Sheets.")
except Exception as e:
    print(f"CRITICAL ERROR: Could not load spreadsheet: {e}")
    exit(1)

# 3. COORDINATE ALIGNMENT
geo_cols = ["Start Lat", "Start Lon", "End Lat", "End Lon"]

for col in geo_cols:
    if col in df.columns:
        df[col] = pd.to_numeric(df[col], errors='coerce')
    else:
        print(f"ERROR: Could not find column '{col}'.")
        exit(1)

df_clean = df.dropna(subset=geo_cols).copy()
print(f"Processing {len(df_clean)} valid walks with coordinates.")

if df_clean.empty:
    print("ERROR: No valid coordinates found.")
    exit(1)

# 4. MAP GENERATION
avg_lat = df_clean["Start Lat"].mean()
avg_lon = df_clean["Start Lon"].mean()
m = folium.Map(location=[avg_lat, avg_lon], zoom_start=14, tiles="OpenStreetMap")

side_colors = {
    "N": "blue", "S": "red", "E": "green", "W": "purple", 
    "BOTH": "orange", "UNKNOWN": "gray"
}

fg_colored = folium.FeatureGroup(name="Color Coded by Side")
fg_coverage = folium.FeatureGroup(name="Plain Coverage", show=False)

# --- THE NEW ROUTING ENGINE ---
def get_route(start_lat, start_lon, end_lat, end_lon):
    # OSRM expects coordinates in {longitude},{latitude} format
    url = f"http://router.project-osrm.org/route/v1/foot/{start_lon},{start_lat};{end_lon},{end_lat}?overview=full&geometries=geojson"
    try:
        r = requests.get(url, timeout=10)
        data = r.json()
        if data.get("code") == "Ok":
            # OSRM returns [lon, lat], but Folium draws using [lat, lon]. We have to flip them!
            coords = data["routes"][0]["geometry"]["coordinates"]
            return [[lat, lon] for lon, lat in coords]
    except Exception as e:
        print(f"OSRM Error: {e}")
    
    # The Safety Net: If routing fails, return the straight line
    return [[start_lat, start_lon], [end_lat, end_lon]]

# 5. DRAW THE LINES
for index, row in df_clean.iterrows():
    start_lat, start_lon = row["Start Lat"], row["Start Lon"]
    end_lat, end_lon = row["End Lat"], row["End Lon"]
    
    print(f"Fetching street route for walk {index + 1}...")
    route_coords = get_route(start_lat, start_lon, end_lat, end_lon)
    
    raw_side = str(row.get("Side", "UNKNOWN")).strip().upper()
    line_color = side_colors.get(raw_side, "gray")
    popup_msg = f"<b>{row.get('Street Name', 'Unknown St')}</b><br>Side: {raw_side}"
    
    # Draw colored line
    folium.PolyLine(
        locations=route_coords,
        weight=6,
        color=line_color,
        opacity=0.8,
        popup=popup_msg
    ).add_to(fg_colored)
    
    # Draw plain coverage line
    folium.PolyLine(
        locations=route_coords,
        weight=6,
        color="#003399", 
        opacity=0.7,
        popup=popup_msg
    ).add_to(fg_coverage)
    
    # Be polite to the free server
    time.sleep(1)

# Add layers and menu to the map
fg_colored.add_to(m)
fg_coverage.add_to(m)
folium.LayerControl().add_to(m)

# 6. SAVE
m.save("manhattan_walklog_map.html")
print("SUCCESS: manhattan_walklog_map.html generated with street snapping.")

# 7. TIMESTAMP CACHE
if "Timestamp" in df_clean.columns:
    latest_ts = str(df_clean["Timestamp"].iloc[-1])
    with open("last_run.txt", "w") as f:
        f.write(latest_ts)
