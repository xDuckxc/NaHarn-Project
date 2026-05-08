"""Volume-based zone mapping for 3D mall visualization."""
import json
from typing import TypedDict

class BoundingBox(TypedDict):
    """3D bounding box definition."""
    min_x: float
    min_y: float
    min_z: float
    max_x: float
    max_y: float
    max_z: float
    center_x: float
    center_y: float
    center_z: float
    width: float
    height: float
    depth: float

# Mall dimensions
MALL_LENGTH = 100.0
MALL_WIDTH = 50.0
MALL_HEIGHT = 4.0

# Zone configuration
ZONE_WIDTH = 20.0
ZONE_CONFIGS = {
    "A": {"start_x": 0.0, "color": "#FF6B6B"},
    "B": {"start_x": 20.0, "color": "#4ECDC4"},
    "C": {"start_x": 40.0, "color": "#45B7D1"},
    "D": {"start_x": 60.0, "color": "#FFA07A"},
    "E": {"start_x": 80.0, "color": "#98D8C8"},
}

def create_zone_volume(zone: str) -> BoundingBox:
    """Create bounding box volume for a zone."""
    config = ZONE_CONFIGS[zone]
    min_x = config["start_x"]
    max_x = min_x + ZONE_WIDTH
    
    return {
        "min_x": min_x,
        "min_y": 0.0,
        "min_z": 0.0,
        "max_x": max_x,
        "max_y": MALL_HEIGHT,
        "max_z": MALL_WIDTH,
        "center_x": min_x + ZONE_WIDTH / 2,
        "center_y": MALL_HEIGHT / 2,
        "center_z": MALL_WIDTH / 2,
        "width": ZONE_WIDTH,
        "height": MALL_HEIGHT,
        "depth": MALL_WIDTH,
    }

def create_section_volume(zone: str, section: int) -> BoundingBox:
    """Create bounding box for a specific section."""
    zone_config = ZONE_CONFIGS[zone]
    min_x = zone_config["start_x"]
    max_x = min_x + ZONE_WIDTH
    
    section_depth = 3.0
    min_z = (section - 1) * section_depth
    max_z = section * section_depth
    
    return {
        "min_x": min_x,
        "min_y": 0.0,
        "min_z": min_z,
        "max_x": max_x,
        "max_y": MALL_HEIGHT,
        "max_z": max_z,
        "center_x": min_x + ZONE_WIDTH / 2,
        "center_y": MALL_HEIGHT / 2,
        "center_z": min_z + section_depth / 2,
        "width": ZONE_WIDTH,
        "height": MALL_HEIGHT,
        "depth": section_depth,
    }

def create_shelf_volume(zone: str, section: int, shelf: int) -> BoundingBox:
    """Create bounding box for a specific shelf."""
    zone_config = ZONE_CONFIGS[zone]
    zone_start = zone_config["start_x"]
    
    shelf_width = 2.5
    shelf_depth = 0.8
    section_depth = 3.0
    
    # Calculate X position
    if shelf <= 3:
        # Right side
        min_x = zone_start + 1.0 + (shelf - 1) * shelf_width
    else:
        # Left side
        min_x = zone_start + ZONE_WIDTH - 8.5 - (shelf - 4) * shelf_width
    max_x = min_x + shelf_width
    
    # Z position
    min_z = (section - 1) * section_depth
    max_z = min_z + shelf_depth
    
    return {
        "min_x": min_x,
        "min_y": 0.0,
        "min_z": min_z,
        "max_x": max_x,
        "max_y": MALL_HEIGHT,
        "max_z": max_z,
        "center_x": (min_x + max_x) / 2,
        "center_y": MALL_HEIGHT / 2,
        "center_z": (min_z + max_z) / 2,
        "width": shelf_width,
        "height": MALL_HEIGHT,
        "depth": shelf_depth,
    }

def generate_all_zone_volumes() -> dict:
    """Generate all zone volumes for 3D visualization."""
    volumes = {}
    for zone in ZONE_CONFIGS:
        volumes[zone] = {
            "zone": zone,
            "color": ZONE_CONFIGS[zone]["color"],
            "volume": create_zone_volume(zone),
        }
    return volumes

def generate_zone_volumes_json() -> str:
    """Generate JSON for Three.js visualization."""
    volumes = generate_all_zone_volumes()
    return json.dumps(volumes, indent=2)

def point_in_zone(x: float, y: float, z: float, zone: str) -> bool:
    """Check if a point is inside a zone volume."""
    bbox = create_zone_volume(zone)
    return (
        bbox["min_x"] <= x <= bbox["max_x"]
        and bbox["min_y"] <= y <= bbox["max_y"]
        and bbox["min_z"] <= z <= bbox["max_z"]
    )

def get_zone_from_coordinates(x: float, y: float, z: float) -> str | None:
    """Get zone letter from 3D coordinates."""
    for zone in ZONE_CONFIGS:
        if point_in_zone(x, y, z, zone):
            return zone
    return None

if __name__ == "__main__":
    print("Zone Volumes:")
    print("=" * 60)
    
    for zone in ["A", "B", "C", "D", "E"]:
        vol = create_zone_volume(zone)
        print(f"\nZone {zone}:")
        print(f"  X: {vol['min_x']:.1f} to {vol['max_x']:.1f}m")
        print(f"  Y: {vol['min_y']:.1f} to {vol['max_y']:.1f}m")
        print(f"  Z: {vol['min_z']:.1f} to {vol['max_z']:.1f}m")
        print(f"  Center: ({vol['center_x']:.1f}, {vol['center_y']:.1f}, {vol['center_z']:.1f})")
        print(f"  Dimensions: {vol['width']:.1f} × {vol['height']:.1f} × {vol['depth']:.1f}m")
    
    print("\n" + "=" * 60)
    print("\nSample Section Volume (Zone C, Section 5):")
    sec_vol = create_section_volume("C", 5)
    print(f"  X: {sec_vol['min_x']:.1f} to {sec_vol['max_x']:.1f}m")
    print(f"  Z: {sec_vol['min_z']:.1f} to {sec_vol['max_z']:.1f}m")
    
    print("\nSample Shelf Volume (Zone A, Section 1, Shelf 3):")
    shelf_vol = create_shelf_volume("A", 1, 3)
    print(f"  X: {shelf_vol['min_x']:.1f} to {shelf_vol['max_x']:.1f}m")
    print(f"  Z: {shelf_vol['min_z']:.1f} to {shelf_vol['max_z']:.1f}m")
    
    print("\n" + "=" * 60)
    print("\nTest point_in_zone:")
    test_points = [
        (10.0, 1.0, 25.0, "A"),
        (30.0, 1.0, 25.0, "B"),
        (50.0, 1.0, 25.0, "C"),
    ]
    for x, y, z, expected in test_points:
        detected = get_zone_from_coordinates(x, y, z)
        status = "✓" if detected == expected else "✗"
        print(f"  {status} ({x}, {y}, {z}) → Zone {detected} (expected {expected})")
