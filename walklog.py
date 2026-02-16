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

# 3. COORDINATE ALIGNMENT (Columns L-O)
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

# 5. DRAW THE LINES
for _, row in df_clean.iterrows():
    start_coords = [row["Start Lat"], row["Start Lon"]]
    end_coords = [row["End Lat"], row["End Lon"]]
    
    # Use 'Side' as found in your log headers
    raw_side = str(row.get("Side", "UNKNOWN")).strip().upper()
    line_color = side_colors.get(raw_side, "gray")
    
    popup_msg = f"<b>{row.get('Street Name', 'Unknown St')}</b><br>Side: {raw_side}"
    
    # Corrected syntax: .add_to(m) instead of .add(m)
    folium.PolyLine(
        locations=[start_coords, end_coords],
        weight=6,
        color=line_color,
        opacity=0.8,
        popup=popup_msg
    ).add_to(m)

# 6. SAVE
m.save("manhattan_walklog_map.html")
print("SUCCESS: manhattan_walklog_map.html generated.")

# 7. TIMESTAMP CACHE
if "Timestamp" in df_clean.columns:
    latest_ts = str(df_clean["Timestamp"].iloc[-1])
    with open("last_run.txt", "w") as f:
        f.write(latest_ts)
