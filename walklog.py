import pandas as pd
import folium
import math
import os

# 1. SETTINGS & URL
SHEET_CSV_URL = "https://docs.google.com/spreadsheets/d/1eTzd_iG590gVdbu6q7p0iDElsCVLr9QTSP1wRWagozg/export?format=csv&gid=1407515623"

print("--- STARTING MANHATTAN WALKLOG UPDATE ---")

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
print(f"Headers found in sheet: {list(df.columns)}")

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

# Layers for toggling
fg_colored = folium.FeatureGroup(name="Color Coded by Side")
fg_coverage = folium.FeatureGroup(name="Plain Coverage", show=False) 

# 5. DRAW THE LINES
for _, row in df_clean.iterrows():
    start_lat, start_lon = row["Start Lat"], row["Start Lon"]
    end_lat, end_lon = row["End Lat"], row["End Lon"]
    
    raw_side = str(row.get("Side", "UNKNOWN")).strip().upper()
    line_color = side_colors.get(raw_side, "gray")
    
    # --- THE NUDGE LOGIC ---
    lat_nudge = 0.00003  # ~10 feet North/South
    lon_nudge = 0.00004  # ~10 feet East/West

    lat_shift = 0
    lon_shift = 0

    if raw_side == "N":
        lat_shift = lat_nudge
    elif raw_side == "S":
        lat_shift = -lat_nudge
    elif raw_side == "E":
        lon_shift = lon_nudge
    elif raw_side == "W":
        lon_shift = -lon_nudge

    # Apply shift to start and end
    start_coords = [start_lat + lat_shift, start_lon + lon_shift]
    end_coords = [end_lat + lat_shift, end_lon + lon_shift]
    
    # Build the line sequence, starting with the first coordinate
    path_locations = [start_coords]
    
    # Check for Midpoint 1 and add it to the path if it exists
    if "Mid 1 Lat" in df.columns and "Mid 1 Lon" in df.columns:
        m1_lat, m1_lon = row.get("Mid 1 Lat"), row.get("Mid 1 Lon")
        if pd.notna(m1_lat) and pd.notna(m1_lon):
            path_locations.append([m1_lat + lat_shift, m1_lon + lon_shift])
            
    # Check for Midpoint 2 and add it to the path if it exists
    if "Mid 2 Lat" in df.columns and "Mid 2 Lon" in df.columns:
        m2_lat, m2_lon = row.get("Mid 2 Lat"), row.get("Mid 2 Lon")
        if pd.notna(m2_lat) and pd.notna(m2_lon):
            path_locations.append([m2_lat + lat_shift, m2_lon + lon_shift])
            
    # Check for Midpoint 3 and add it to the path if it exists
    if "Mid 3 Lat" in df.columns and "Mid 3 Lon" in df.columns:
        m3_lat, m3_lon = row.get("Mid 3 Lat"), row.get("Mid 3 Lon")
        if pd.notna(m3_lat) and pd.notna(m3_lon):
            path_locations.append([m3_lat + lat_shift, m3_lon + lon_shift])
    
    # Check for Midpoint 4 and add it to the path if it exists
    if "Mid 4 Lat" in df.columns and "Mid 4 Lon" in df.columns:
        m4_lat, m4_lon = row.get("Mid 4 Lat"), row.get("Mid 4 Lon")
        if pd.notna(m4_lat) and pd.notna(m4_lon):
            path_locations.append([m4_lat + lat_shift, m4_lon + lon_shift])

    # Check for Midpoint 5 and add it to the path if it exists
    if "Mid 5 Lat" in df.columns and "Mid 5 Lon" in df.columns:
        m5_lat, m5_lon = row.get("Mid 5 Lat"), row.get("Mid 5 Lon")
        if pd.notna(m5_lat) and pd.notna(m5_lon):
            path_locations.append([m5_lat + lat_shift, m5_lon + lon_shift])
            
    # Cap the path off with the final coordinate
    path_locations.append(end_coords)
    
    popup_msg = f"<b>{row.get('Street Name', 'Unknown St')}</b><br>Side: {raw_side}"
    
    # Draw colored line
    folium.PolyLine(
        locations=path_locations,
        weight=6,
        color=line_color,
        opacity=0.8,
        popup=popup_msg
    ).add_to(fg_colored)
    
    # Draw plain coverage line
    folium.PolyLine(
        locations=path_locations,
        weight=6,
        color="#003399", 
        opacity=0.7,
        popup=popup_msg
    ).add_to(fg_coverage)

# Add layers and menu
fg_colored.add_to(m)
fg_coverage.add_to(m)
folium.LayerControl().add_to(m)

# 6. SAVE
m.save("manhattan_walklog_map.html")
print("SUCCESS: manhattan_walklog_map.html generated.")

# 7. TIMESTAMP CACHE
if "Timestamp" in df_clean.columns:
    latest_ts = str(df_clean["Timestamp"].iloc[-1])
    with open("last_run.txt", "w") as f:
        f.write(latest_ts)

