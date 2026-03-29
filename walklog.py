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

# 8 distinct colors mapping to the combined "Side-Direction" string
side_colors = {
    "N-E": "#e6194B", # Red
    "N-W": "#3cb44b", # Green
    "S-E": "#ffe119", # Yellow
    "S-W": "#4363d8", # Blue
    "E-N": "#f58231", # Orange
    "E-S": "#911eb4", # Purple
    "W-N": "#46f0f0", # Cyan
    "W-S": "#f032e6", # Magenta
    "UNKNOWN": "gray"
}

# Layers for toggling
fg_coverage = folium.FeatureGroup(name="Plain Coverage", show=True) 
fg_colored = folium.FeatureGroup(name="Color Coded by Side & Direction", show=False)

# 5. DRAW THE LINES
for _, row in df_clean.iterrows():
    start_lat, start_lon = row["Start Lat"], row["Start Lon"]
    end_lat, end_lon = row["End Lat"], row["End Lon"]
    
    # Grab both Side and Direction columns separately
    raw_side = str(row.get("Side", "")).strip().upper()
    raw_dir = str(row.get("Direction", "")).strip().upper()
    
    # Combine them to match our dictionary keys (e.g., "N-E")
    if raw_side and raw_dir and raw_side != "NAN" and raw_dir != "NAN":
        combo_key = f"{raw_side}-{raw_dir}"
    else:
        combo_key = "UNKNOWN"
        
    line_color = side_colors.get(combo_key, "gray")
    
    # --- THE NUDGE LOGIC ---
    lat_nudge = 0.00003  # ~10 feet North/South
    lon_nudge = 0.00004  # ~10 feet East/West

    lat_shift = 0
    lon_shift = 0

    # We only shift based on the SIDE of the street walked
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
    
    # Build the line sequence
    path_locations = [start_coords]
    
    # Check for Midpoints 1 through 5 dynamically
    for i in range(1, 6):
        mid_lat_col = f"Mid {i} Lat"
        mid_lon_col = f"Mid {i} Lon"
        if mid_lat_col in df.columns and mid_lon_col in df.columns:
            m_lat, m_lon = row.get(mid_lat_col), row.get(mid_lon_col)
            if pd.notna(m_lat) and pd.notna(m_lon):
                path_locations.append([m_lat + lat_shift, m_lon + lon_shift])
            
    # Cap the path off with the final coordinate
    path_locations.append(end_coords)
    
    popup_msg = f"<b>{row.get('Street Name', 'Unknown St')}</b><br>Side: {raw_side}<br>Dir: {raw_dir}"
    
    # Draw plain coverage line
    folium.PolyLine(
        locations=path_locations,
        weight=6,
        color="#003399", 
        opacity=0.7,
        popup=popup_msg
    ).add_to(fg_coverage)
    
    # Draw colored line
    folium.PolyLine(
        locations=path_locations,
        weight=6,
        color=line_color,
        opacity=0.8,
        popup=popup_msg
    ).add_to(fg_colored)

# Add layers and menu
fg_coverage.add_to(m)
fg_colored.add_to(m)
folium.LayerControl().add_to(m)

# 6. SAVE
m.save("manhattan_walklog_map.html")
print("SUCCESS: manhattan_walklog_map.html generated.")

# 7. TIMESTAMP CACHE
if "Timestamp" in df_clean.columns:
    latest_ts = str(df_clean["Timestamp"].iloc[-1])
    with open("last_run.txt", "w") as f:
        f.write(latest_ts)
