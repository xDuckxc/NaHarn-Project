"""Mall layout configuration for 3D navigation system."""

# Mall dimensions (meters)
MALL_LENGTH = 100.0  # Total length (X-axis)
MALL_WIDTH = 50.0    # Total width (Z-axis)
MALL_HEIGHT = 4.0    # Ceiling height

# Zone configuration (5 zones: A, B, C, D, E)
ZONE_WIDTH = 20.0    # Each zone is 20m wide
ZONE_COUNT = 5

# Zone X positions (start of each zone)
ZONE_X = {
    "A": 0.0,
    "B": 20.0,
    "C": 40.0,
    "D": 60.0,
    "E": 80.0
}

# Section configuration
SECTION_DEPTH = 3.0      # Each section is 3m deep (Z-axis)
SECTION_WIDTH = 18.0     # Usable width within zone (leaving 1m margins)
AISLE_WIDTH = 2.0        # Main aisle width between sections

# Shelf configuration
SHELF_COUNT_PER_SECTION = 6  # 3 shelves on each side
SHELF_WIDTH = 2.5            # Each shelf unit is 2.5m wide
SHELF_DEPTH = 0.8            # Shelf depth
SHELF_HEIGHT = 0.8           # Distance between shelf levels
SHELF_LEVELS = 3             # Bottom, eye-level, top

# Shelf positioning within section
# Shelves 1-3: Right side (positive X offset from zone start)
# Shelves 4-6: Left side (negative X offset from zone start)
SHELF_SIDE_OFFSET = 1.0  # Distance from zone edge to first shelf

def get_zone_center(zone: str) -> tuple[float, float, float]:
    """Get center point of a zone."""
    x = ZONE_X.get(zone, 0) + ZONE_WIDTH / 2
    y = MALL_HEIGHT / 2
    z = MALL_WIDTH / 2
    return (x, y, z)

def get_section_position(zone: str, section: int) -> tuple[float, float, float]:
    """Get center position of a section within a zone."""
    zone_x = ZONE_X.get(zone, 0)
    x = zone_x + ZONE_WIDTH / 2
    y = 0.0  # Ground level
    z = section * SECTION_DEPTH
    return (x, y, z)

def get_shelf_position(zone: str, section: int, shelf: int, shelf_level: int) -> tuple[float, float, float]:
    """
    Calculate precise 3D position for a shelf.
    
    Args:
        zone: Zone letter (A-E)
        section: Section number (1-n)
        shelf: Shelf number (1-6)
            1-3: Right side of aisle
            4-6: Left side of aisle
        shelf_level: Shelf level (1-3)
            1: Bottom shelf
            2: Eye level
            3: Top shelf
    
    Returns:
        (x, y, z) coordinates in meters
    """
    zone_x = ZONE_X.get(zone, 0)
    
    # X position: zone start + shelf offset
    if shelf <= 3:
        # Right side (shelves 1-3)
        shelf_index = shelf - 1
        x = zone_x + SHELF_SIDE_OFFSET + (shelf_index * SHELF_WIDTH)
    else:
        # Left side (shelves 4-6)
        shelf_index = shelf - 4
        x = zone_x + ZONE_WIDTH - SHELF_SIDE_OFFSET - (shelf_index * SHELF_WIDTH) - SHELF_WIDTH
    
    # Y position: height based on shelf level
    y = (shelf_level - 1) * SHELF_HEIGHT + 0.5  # 0.5m base height
    
    # Z position: section depth
    z = section * SECTION_DEPTH
    
    return (round(x, 2), round(y, 2), round(z, 2))

def get_navigation_waypoints(zone: str, section: int) -> list[tuple[float, float, float]]:
    """
    Get waypoints for navigating to a specific section.
    Returns list of (x, y, z) coordinates for path planning.
    """
    waypoints = []
    
    # Start at zone entrance
    zone_x = ZONE_X.get(zone, 0)
    waypoints.append((zone_x + ZONE_WIDTH / 2, 0.0, 0.0))
    
    # Move to section
    section_pos = get_section_position(zone, section)
    waypoints.append(section_pos)
    
    return waypoints

# Shelf layout visualization
SHELF_LAYOUT = """
Mall Layout (Top View):

Zone A (0-20m)  | Zone B (20-40m) | Zone C (40-60m) | Zone D (60-80m) | Zone E (80-100m)
----------------|-----------------|-----------------|-----------------|------------------
[1][2][3]       | [1][2][3]       | [1][2][3]       | [1][2][3]       | [1][2][3]
   AISLE        |    AISLE        |    AISLE        |    AISLE        |    AISLE
[4][5][6]       | [4][5][6]       | [4][5][6]       | [4][5][6]       | [4][5][6]

Each [n] represents a shelf unit (2.5m wide)
Sections run perpendicular (Z-axis, 3m deep each)
"""

if __name__ == "__main__":
    print(SHELF_LAYOUT)
    print("\nSample positions:")
    
    # Test positions
    test_cases = [
        ("A", 1, 1, 2),  # Zone A, Section 1, Shelf 1, Level 2
        ("C", 5, 3, 1),  # Zone C, Section 5, Shelf 3, Level 1
        ("E", 3, 6, 3),  # Zone E, Section 3, Shelf 6, Level 3
    ]
    
    for zone, section, shelf, level in test_cases:
        x, y, z = get_shelf_position(zone, section, shelf, level)
        print(f"Zone {zone}, Section {section}, Shelf {shelf}, Level {level}: ({x}, {y}, {z})")
