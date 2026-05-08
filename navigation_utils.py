"""Navigation utilities for 3D mall system."""
import sys
from pathlib import Path

# Import mall layout config
sys.path.insert(0, str(Path(__file__).parent / "scripts"))
from mall_layout_config import (
    get_shelf_position,
    get_section_position,
    get_zone_center,
    get_navigation_waypoints,
    ZONE_X,
    ZONE_WIDTH,
    SECTION_DEPTH
)

def get_product_waypoints(products: list[dict]) -> list[dict]:
    """
    Generate navigation waypoints for a list of products.
    Returns waypoints sorted by optimal walking path.
    """
    if not products:
        return []
    
    waypoints = []
    for product in products:
        coords = product.get("coordinates_3d", {})
        location = product.get("location_info", {})
        
        if not coords or not location:
            continue
        
        waypoints.append({
            "product_id": product.get("id"),
            "product_name": product.get("name"),
            "zone": location.get("zone"),
            "section": int(location.get("section", 0)),
            "shelf": int(location.get("shelf", 0)),
            "coordinates": coords,
            "sort_key": (
                location.get("zone", "Z"),
                int(location.get("section", 999)),
                int(location.get("shelf", 999))
            )
        })
    
    # Sort by zone → section → shelf for optimal path
    waypoints.sort(key=lambda w: w["sort_key"])
    return waypoints

def format_navigation_instructions(waypoints: list[dict]) -> str:
    """Format waypoints into human-readable navigation instructions."""
    if not waypoints:
        return "ไม่มีเส้นทาง"
    
    instructions = []
    current_zone = None
    
    for i, wp in enumerate(waypoints, 1):
        zone = wp["zone"]
        section = wp["section"]
        shelf = wp["shelf"]
        name = wp["product_name"]
        
        if zone != current_zone:
            instructions.append(f"\n**โซน {zone}**")
            current_zone = zone
        
        side = "ฝั่งขวา" if shelf <= 3 else "ฝั่งซ้าย"
        instructions.append(
            f"{i}. {name} — Section {section}, Shelf {shelf} ({side})"
        )
    
    return "\n".join(instructions)

def calculate_walking_distance(waypoints: list[dict]) -> float:
    """Calculate approximate walking distance in meters."""
    if len(waypoints) < 2:
        return 0.0
    
    total_distance = 0.0
    for i in range(len(waypoints) - 1):
        curr = waypoints[i]["coordinates"]
        next_wp = waypoints[i + 1]["coordinates"]
        
        # Simple Manhattan distance (walking along aisles)
        dx = abs(next_wp["x"] - curr["x"])
        dz = abs(next_wp["z"] - curr["z"])
        total_distance += dx + dz
    
    return round(total_distance, 1)

__all__ = [
    "get_product_waypoints",
    "format_navigation_instructions",
    "calculate_walking_distance",
    "get_shelf_position",
    "get_section_position",
    "get_zone_center",
]
