#!/usr/bin/env python3
"""Generate 3D coordinates for products based on location_info."""
import csv
import json
from pathlib import Path
import sys

# Import mall layout configuration
sys.path.insert(0, str(Path(__file__).parent))
from mall_layout_config import get_shelf_position

def calculate_3d_position(location_info):
    """Calculate (x, y, z) from location_info JSON using mall layout config."""
    zone = location_info.get("zone", "A")
    section = int(location_info.get("section", 1))
    shelf = int(location_info.get("shelf", 1))
    shelf_level = int(location_info.get("shelf_level", 1))
    
    x, y, z = get_shelf_position(zone, section, shelf, shelf_level)
    return {"x": x, "y": y, "z": z}

def main():
    csv_path = Path("mall_products_500.csv")
    output_path = Path("mall_products_500_with_3d.csv")
    
    rows = []
    with csv_path.open(encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames + ["coordinates_3d"]
        
        for row in reader:
            location_info = json.loads(row["location_info"])
            coords_3d = calculate_3d_position(location_info)
            row["coordinates_3d"] = json.dumps(coords_3d, ensure_ascii=False)
            rows.append(row)
    
    with output_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    
    print(f"✓ Generated 3D coordinates for {len(rows)} products")
    print(f"✓ Saved to {output_path}")
    print(f"\nSample coordinates:")
    for row in rows[:3]:
        print(f"  ID {row['id']}: {row['name'][:30]} → {row['coordinates_3d']}")

if __name__ == "__main__":
    main()
