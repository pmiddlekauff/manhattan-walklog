import pandas as pd
import folium
import math
import os
from branca.element import Template, MacroElement

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
    
    raw_side = str(row.get("Side", "")).strip().upper()
    raw_dir = str(row.get("Direction", "")).strip().upper()
    
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

    if raw_side == "N":
        lat_shift = lat_nudge
    elif raw_side == "S":
        lat_shift = -lat_nudge
    elif raw_side == "E":
        lon_shift = lon_nudge
    elif raw_side == "W":
        lon_shift = -lon_nudge

    start_coords = [start_lat + lat_shift, start_lon + lon_shift]
    end_coords = [end_lat + lat_shift, end_lon + lon_shift]
    
    path_locations = [start_coords]
    
    for i in range(1, 6):
        mid_lat_col = f"Mid {i} Lat"
        mid_lon_col = f"Mid {i} Lon"
        if mid_lat_col in df.columns and mid_lon_col in df.columns:
            m_lat, m_lon = row.get(mid_lat_col), row.get(mid_lon_col)
            if pd.notna(m_lat) and pd.notna(m_lon):
                path_locations.append([m_lat + lat_shift, m_lon + lon_shift])
            
    path_locations.append(end_coords)
    
    popup_msg = f"<b>{row.get('Street Name', 'Unknown St')}</b><br>Side: {raw_side}<br>Dir: {raw_dir}"
    
    folium.PolyLine(
        locations=path_locations,
        weight=6,
        color="#003399", 
        opacity=0.7,
        popup=popup_msg
    ).add_to(fg_coverage)
    
    folium.PolyLine(
        locations=path_locations,
        weight=6,
        color=line_color,
        opacity=0.8,
        popup=popup_msg
    ).add_to(fg_colored)

fg_coverage.add_to(m)
fg_colored.add_to(m)
folium.LayerControl().add_to(m)

# 6. DYNAMIC LEGEND GENERATION
legend_template = """
{% macro html(this, kwargs) %}
<div id='maplegend' class='maplegend'>
<div class='legend-title'>Side & Direction</div>
<div class='legend-scale'>
  <ul class='legend-labels'>
    <li><span></span>North Side, Eastbound (N-E)</li>
    <li><span style='background:#3cb44b;'></span>North Side, Westbound (N-W)</li>
    <li><span style='background:#ffe119;'></span>South Side, Eastbound (S-E)</li>
    <li><span style='background:#4363d8;'></span>South Side, Westbound (S-W)</li>
    <li><span style='background:#f58231;'></span>East Side, Northbound (E-N)</li>
    <li><span style='background:#911eb4;'></span>East Side, Southbound (E-S)</li>
    <li><span style='background:#46f0f0;'></span>West Side, Northbound (W-N)</li>
    <li><span style='background:#f032e6;'></span>West Side, Southbound (W-S)</li>
    <li><span style='background:gray;'></span>Unknown</li>
  </ul>
</div>
</div>

<style type='text/css'>
  /* Default Desktop Styles */
  .maplegend {
    position: absolute; z-index:9999; border:2px solid grey; 
    background-color:rgba(255, 255, 255, 0.9); border-radius:6px; 
    padding: 10px; font-size:14px; right: 20px; bottom: 20px; display: none;
  }
  .maplegend .legend-title { text-align: left; margin-bottom: 5px; font-weight: bold; font-size: 90%; }
  .maplegend .legend-scale ul { margin: 0; padding: 0; list-style: none; }
  .maplegend .legend-scale ul li { font-size: 80%; list-style: none; line-height: 18px; margin-bottom: 2px; }
  .maplegend ul.legend-labels li span { display: block; float: left; height: 16px; width: 30px; margin-right: 5px; border: 1px solid #999; }
  
  /* Mobile Styles (Triggers on phone screens) */
  @media (max-width: 600px) {
    .maplegend {
      right: 10px; bottom: 30px; /* Shifts up to avoid iOS home bar */
      padding: 6px; font-size: 11px; /* Shrinks overall text size */
      max-width: 180px; /* Prevents stretching across the screen */
    }
    .maplegend .legend-scale ul li { line-height: 14px; margin-bottom: 4px; }
    .maplegend ul.legend-labels li span { height: 12px; width: 20px; } /* Shrinks the color boxes */
  }
</style>

<script>
document.addEventListener("DOMContentLoaded", function(event) {
    setTimeout(function() {
        var map_keys = Object.keys(window).filter(k => k.startsWith('map_'));
        if(map_keys.length > 0) {
            var myMap = window[map_keys[0]];
            
            myMap.on('overlayadd', function(eventLayer) {
                if (eventLayer.name === 'Color Coded by Side & Direction') {
                    document.getElementById('maplegend').style.display = 'block';
                }
            });
            
            myMap.on('overlayremove', function(eventLayer) {
                if (eventLayer.name === 'Color Coded by Side & Direction') {
                    document.getElementById('maplegend').style.display = 'none';
                }
            });
        }
    }, 500);
});
</script>
{% endmacro %}
"""

# 7. SAVE
m.save("manhattan_walklog_map.html")
print("SUCCESS: manhattan_walklog_map.html generated.")

# 8. TIMESTAMP CACHE
if "Timestamp" in df_clean.columns:
    latest_ts = str(df_clean["Timestamp"].iloc[-1])
    with open("last_run.txt", "w") as f:
        f.write(latest_ts)
