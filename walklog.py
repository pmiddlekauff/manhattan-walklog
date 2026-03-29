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

# 8 distinct, high-contrast colors. 
# IMPORTANT: Update keys like "N-E" to match the exact text in your "Side" column!
side_colors = {
    "N-E": "#e6194B", # Red
    "N-W": "#3cb44b", # Green
    "S-E": "#ffe119", # Yellow
    "S-W": "#4363d8", # Blue
    "E-N": "#f58231", # Orange
    "E-S": "#911eb4", # Purple
    "W-N": "#46f0f0", # Cyan
    "W-S": "#f032e6", # Magenta
    "BOTH": "white",
    "UNKNOWN": "gray"
}

# Layers for toggling - Default views swapped here
fg_coverage = folium.FeatureGroup(name="Plain Coverage", show=True)  # Shows by default
fg_colored = folium.FeatureGroup(name="Color Coded by Side", show=False) # Hidden by default

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

    # Checks if the letter is anywhere in the string to allow composite nudging
    if "N" in raw_side:
        lat_shift += lat_nudge
    elif "S" in raw_side:
        lat_shift -= lat_nudge

    if "E" in raw_side:
        lon_shift += lon_nudge
    elif "W" in raw_side:
        lon_shift -= lon_nudge

    # Apply shift to start and end
    start_coords = [start_lat + lat_shift, start_lon + lon_shift]
    end_coords = [end_lat + lat_shift, end_lon + lon_shift]
    
    # Build the line sequence, starting with the first coordinate
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
    
    popup_msg = f"<b>{row.get('Street Name', 'Unknown St')}</b><br>Side: {raw_side}"
    
    # Draw plain coverage line (now adding to fg_coverage)
    folium.PolyLine(
        locations=path_locations,
        weight=6,
        color="#003399", 
        opacity=0.7,
        popup=popup_msg
    ).add_to(fg_coverage)
    
    # Draw colored line (now adding to fg_colored)
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
