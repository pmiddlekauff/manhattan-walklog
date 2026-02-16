import pandas as pd
import folium
import math

# 1. Pull the live data directly from your Google Sheet
SHEET_CSV_URL = "https://docs.google.com/spreadsheets/d/1eTzd_iG590gVdbu6q7p0iDElsCVLr9QTSP1wRWagozg/export?format=csv&gid=1407515623"

print("Fetching data from Google Sheets...")
df = pd.read_csv(SHEET_CSV_URL)

# Clean headers
df.columns = df.columns.str.strip()

# 2. THE FIX: Convert all empty spreadsheet cells into safe, blank strings
# This prevents 'NaN' floats from crashing the HTML/Javascript map renderer
df = df.fillna("")

# 3. Ensure coordinates are strict numbers
geo_cols = ["Start Lat", "Start Lon", "End Lat", "End Lon"]
for col in geo_cols:
    df[col] = pd.to_numeric(df[col], errors='coerce')

# Drop rows that don't have coordinates yet
df = df.dropna(subset=geo_cols)

if df.empty:
    print("No valid coordinates found. Exiting.")
    exit()

print(f"Loaded {len(df)} walks. Drawing map...")

import os # Add this to your imports at the top of the file

# --- INSERT THIS AFTER df = df.dropna(...) AND BEFORE GEOCODING ---

# 1. Identify the timestamp of the most recent walk
# Assuming your first column is named 'Timestamp'
latest_timestamp = str(df['Timestamp'].iloc[-1])

# 2. Check the memory file
cache_file = 'last_run.txt'

if os.path.exists(cache_file):
    with open(cache_file, 'r') as f:
        last_timestamp = f.read().strip()
    
    # 3. The Gate: If the timestamps match, stop the script entirely
    if latest_timestamp == last_timestamp:
        print(f"No new walks logged since {last_timestamp}. Exiting to save processing power.")
        exit()

print(f"New walk detected: {latest_timestamp}. Generating new map...")

# ... [Rest of your script runs here] ...

# 4. Save the new timestamp at the very bottom of your file (after m.save(out))
with open(cache_file, 'w') as f:
    f.write(latest_timestamp)

# ==========================================
# FOLIUM MAP GENERATION
# ==========================================

# Standardize column mapping safely
side_col = "Side of Street" if "Side of Street" in df.columns else "Side"
dir_col = "Direction"

# Bounds + center
pts = df[["Start Lat","Start Lon"]].values.tolist() + df[["End Lat","End Lon"]].values.tolist()
min_lat = min(p[0] for p in pts); max_lat = max(p[0] for p in pts)
min_lon = min(p[1] for p in pts); max_lon = max(p[1] for p in pts)
center = [(min_lat+max_lat)/2, (min_lon+max_lon)/2]

def bearing_deg(lat1, lon1, lat2, lon2):
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    dlon = math.radians(lon2 - lon1)
    y = math.sin(dlon) * math.cos(phi2)
    x = math.cos(phi1)*math.sin(phi2) - math.sin(phi1)*math.cos(phi2)*math.cos(dlon)
    brng = math.degrees(math.atan2(y, x))
    return (brng + 360) % 360

side_colors = {"N":"blue","S":"red","E":"green","W":"purple","BOTH":"orange","UNKNOWN":"gray"}

m = folium.Map(location=center, zoom_start=15, control_scale=True, tiles="OpenStreetMap")

fg_cov = folium.FeatureGroup(name="Coverage (all segments)", show=True)
fg_side = folium.FeatureGroup(name="Side-colored segments", show=True)
fg_dir = folium.FeatureGroup(name="Direction arrows", show=True)

for _, row in df.iterrows():
    # Force native Python floats to prevent numpy serialization errors
    start = (float(row["Start Lat"]), float(row["Start Lon"]))
    end = (float(row["End Lat"]), float(row["End Lon"]))

    # Safely extract text fields
    side = str(row.get(side_col, "UNKNOWN")).strip().upper()
    direction = str(row.get(dir_col, "UNKNOWN")).strip().upper()
    color = side_colors.get(side, "black")

    date_val = str(row.get("Local Time", row.get("Timestamp", "N/A")))
    mode_val = str(row.get("Mode", "Walk"))
    conf_val = str(row.get("Confidence", "High"))
    key_val = str(row.get("Unique ID", "N/A"))
    street_name = str(row.get("Street Name", "Unknown"))
    from_st = str(row.get("From Cross St", "Unknown"))
    to_st = str(row.get("To Cross St", "Unknown"))

    tooltip = f"{street_name}: {from_st} → {to_st} | Side {side} | Dir {direction}"
    
    popup_html = (
        f"<b>{street_name}</b><br>"
        f"{from_st} → {to_st}<br>"
        f"Side: {side}<br>"
        f"Direction: {direction}<br>"
        f"Date: {date_val}<br>"
        f"Mode: {mode_val}<br>"
        f"Confidence: {conf_val}<br>"
        f"Key: {key_val}"
    )
    
    # THE FIX 2: Create two separate popups. Reusing one popup object on two lines breaks Leaflet!
    popup_cov = folium.Popup(popup_html, max_width=350)
    popup_side = folium.Popup(popup_html, max_width=350)

    # Coverage line
    folium.PolyLine([start, end], weight=8, opacity=0.85, tooltip=tooltip, popup=popup_cov).add_to(fg_cov)

    # Side-colored line
    folium.PolyLine([start, end], weight=6, opacity=0.95, color=color, tooltip=tooltip, popup=popup_side).add_to(fg_side)

    # Direction arrow marker
    mid = ((start[0]+end[0])/2, (start[1]+end[1])/2)
    brng = bearing_deg(start[0], start[1], end[0], end[1])  
    rot = brng - 90
    arrow_html = f"""
    <div style="
        font-size:18px;
        transform: rotate({rot}deg);
        transform-origin: center;
        color: {color};
        text-shadow: -1px 0 #fff, 0 1px #fff, 1px 0 #fff, 0 -1px #fff;
    ">➤</div>
    """
    folium.Marker(mid, icon=folium.DivIcon(html=arrow_html), tooltip=f"{street_name} dir").add_to(fg_dir)

fg_cov.add_to(m)
fg_side.add_to(m)
fg_dir.add_to(m)
folium.LayerControl(collapsed=False).add_to(m)

m.fit_bounds([[min_lat, min_lon], [max_lat, max_lon]])

out = "manhattan_walklog_map.html"
m.save(out)
print(f"\nMap successfully saved to {out}! Double-click to view.")