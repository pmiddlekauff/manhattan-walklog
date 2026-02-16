import pandas as pd
import folium
import math
import os

# 1. SETTINGS & URL
# Your specific Google Sheet CSV Export URL
SHEET_CSV_URL = "https://docs.google.com/spreadsheets/d/1eTzd_iG590gVdbu6q7p0iDElsCVLr9QTSP1wRWagozg/export?format=csv&gid=1407515623"

print("--- STARTING MANHATTAN WALKLOG UPDATE ---")

# 2. FETCH DATA
try:
    # We read the CSV and strip any accidental spaces from headers
    df = pd.read_csv(SHEET_CSV_URL)
    df.columns = df.columns.str.strip()
    print(f"Successfully loaded {len(df)} rows from Google Sheets.")
except Exception as e:
    print(f"CRITICAL ERROR: Could not load spreadsheet. Check your Sharing settings. Error: {e}")
    exit(1)

# 3. COORDINATE ALIGNMENT
# These MUST match the headers in your Google Sheet Row 1 exactly
geo_cols = ["Start Lat", "Start Lon", "End Lat", "End Lon"]

print(f"Headers found in sheet: {list(df.columns)}")

# Convert coordinates to numbers, turn errors into "NaN" (Not a Number)
for col in geo_cols:
    if col in df.columns:
        df[col] = pd.to_numeric(df[col], errors='coerce')
    else:
        print(f"ERROR: Could not find column '{col}'. Check your spreadsheet headers.")
        exit(1)

# Drop any rows that are missing coordinates (like empty rows at the bottom)
df_clean = df.dropna(subset=geo_cols).copy()
print(f"Processing {len(df_clean)} valid walks with coordinates.")

if df_clean.empty:
    print("ERROR: No rows found with valid numerical coordinates in L-O.")
    exit(1)

# 4. MAP GENERATION
# Set the center of the map based on your walk data
avg_lat = df_clean["Start Lat"].mean()
avg_lon = df_clean["Start Lon"].mean()
m = folium.Map(location=[avg_lat, avg_lon], zoom_start=14, tiles="OpenStreetMap")

# Define colors for sides of the street
side_colors = {
    "N": "blue", "S": "red", "E": "green", "W": "purple", 
    "BOTH": "orange", "UNKNOWN": "gray"
}

# 5. DRAW THE LINES
for _, row in df_clean.iterrows():
    start_coords = [row["Start Lat"], row["Start Lon"]]
    end_coords = [row["End Lat"], row["End Lon"]]
    
    # Clean up the "Side" value to match our color dictionary
    raw_side = str(row.get("Side of Street", "UNKNOWN")).strip().upper()
    line_color = side_colors.get(raw_side, "gray")
    
    # Create a nice popup when you click a line
    popup_msg = f"<b>{row.get('Street Name', 'Unknown St')}</b><br>Side: {raw_side}"
    
    folium.PolyLine(
        locations=[start_coords, end_coords],
        weight=6,
        color=line_color,
        opacity=0.8,
        popup=popup_msg
    ).add
