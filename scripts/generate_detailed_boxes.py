#!/usr/bin/env python3
"""Generate detailed bounding boxes for sections and shelves."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from mall_layout_config import ZONE_X, ZONE_WIDTH, SECTION_DEPTH, SHELF_WIDTH

def generate_section_boxes(zone: str, max_sections: int = 5):
    """Generate section boxes for a zone."""
    zone_x = ZONE_X.get(zone, 0)
    boxes = []
    
    for section in range(1, max_sections + 1):
        z_min = (section - 1) * SECTION_DEPTH
        z_max = section * SECTION_DEPTH
        z_center = (z_min + z_max) / 2
        
        boxes.append({
            "zone": zone,
            "section": section,
            "x": zone_x + ZONE_WIDTH / 2,
            "y": 2.0,
            "z": z_center,
            "w": ZONE_WIDTH,
            "h": 4.0,
            "d": SECTION_DEPTH,
            "color": 0x888888  # Gray
        })
    
    return boxes

def generate_shelf_boxes(zone: str, section: int):
    """Generate shelf boxes for a specific section."""
    zone_x = ZONE_X.get(zone, 0)
    z_min = (section - 1) * SECTION_DEPTH
    z_center = z_min + SECTION_DEPTH / 2
    
    boxes = []
    
    # Shelves 1-3 (right side)
    for shelf in range(1, 4):
        x = zone_x + 1.0 + (shelf - 1) * SHELF_WIDTH + SHELF_WIDTH / 2
        boxes.append({
            "zone": zone,
            "section": section,
            "shelf": shelf,
            "x": x,
            "y": 2.0,
            "z": z_center,
            "w": SHELF_WIDTH,
            "h": 4.0,
            "d": 0.8,
            "color": 0x00FF00  # Green
        })
    
    # Shelves 4-6 (left side)
    for shelf in range(4, 7):
        x = zone_x + ZONE_WIDTH - 8.5 - (shelf - 4) * SHELF_WIDTH + SHELF_WIDTH / 2
        boxes.append({
            "zone": zone,
            "section": section,
            "shelf": shelf,
            "x": x,
            "y": 2.0,
            "z": z_center,
            "w": SHELF_WIDTH,
            "h": 4.0,
            "d": 0.8,
            "color": 0x0000FF  # Blue
        })
    
    return boxes

def generate_all_detailed_boxes():
    """Generate all section and shelf boxes."""
    all_boxes = {
        "sections": [],
        "shelves": []
    }
    
    # Generate sections for all zones
    for zone in ["A", "B", "C", "D", "E"]:
        all_boxes["sections"].extend(generate_section_boxes(zone, max_sections=5))
    
    # Generate shelves for Zone A, Section 1 (example)
    all_boxes["shelves"].extend(generate_shelf_boxes("A", 1))
    
    return all_boxes

def generate_javascript():
    """Generate JavaScript code for detailed boxes."""
    boxes = generate_all_detailed_boxes()
    
    js_code = """
// Detailed bounding boxes (sections and shelves)
const detailedBoxes = {
    sections: [
"""
    
    for box in boxes["sections"]:
        js_code += f"""        {{ zone: '{box["zone"]}', section: {box["section"]}, x: {box["x"]}, y: {box["y"]}, z: {box["z"]}, w: {box["w"]}, h: {box["h"]}, d: {box["d"]}, color: {hex(box["color"])} }},
"""
    
    js_code += """    ],
    shelves: [
"""
    
    for box in boxes["shelves"]:
        js_code += f"""        {{ zone: '{box["zone"]}', section: {box["section"]}, shelf: {box["shelf"]}, x: {box["x"]}, y: {box["y"]}, z: {box["z"]}, w: {box["w"]}, h: {box["h"]}, d: {box["d"]}, color: {hex(box["color"])} }},
"""
    
    js_code += """    ]
};

// Create detailed boxes
function createDetailedBoxes(scene, showSections = false, showShelves = false) {
    const boxes = [];
    
    if (showSections) {
        detailedBoxes.sections.forEach(box => {
            const geometry = new THREE.BoxGeometry(box.w, box.h, box.d);
            const edges = new THREE.EdgesGeometry(geometry);
            const material = new THREE.LineBasicMaterial({ color: box.color, linewidth: 1 });
            const wireframe = new THREE.LineSegments(edges, material);
            wireframe.position.set(box.x, box.y, box.z);
            wireframe.userData = { type: 'section', zone: box.zone, section: box.section };
            scene.add(wireframe);
            boxes.push(wireframe);
        });
    }
    
    if (showShelves) {
        detailedBoxes.shelves.forEach(box => {
            const geometry = new THREE.BoxGeometry(box.w, box.h, box.d);
            const edges = new THREE.EdgesGeometry(geometry);
            const material = new THREE.LineBasicMaterial({ color: box.color, linewidth: 1 });
            const wireframe = new THREE.LineSegments(edges, material);
            wireframe.position.set(box.x, box.y, box.z);
            wireframe.userData = { type: 'shelf', zone: box.zone, section: box.section, shelf: box.shelf };
            scene.add(wireframe);
            boxes.push(wireframe);
        });
    }
    
    return boxes;
}

// Export
if (typeof module !== 'undefined' && module.exports) {
    module.exports = { detailedBoxes, createDetailedBoxes };
}
"""
    
    return js_code

def main():
    output_path = Path("static/detailed_boxes.js")
    output_path.parent.mkdir(exist_ok=True)
    
    js_code = generate_javascript()
    output_path.write_text(js_code, encoding="utf-8")
    
    boxes = generate_all_detailed_boxes()
    print(f"✓ Generated {output_path}")
    print(f"✓ Sections: {len(boxes['sections'])}")
    print(f"✓ Shelves: {len(boxes['shelves'])}")
    
    # Copy to public
    public_path = Path("public/detailed_boxes.js")
    public_path.write_text(js_code, encoding="utf-8")
    print(f"✓ Copied to {public_path}")
    
    # Print sample
    print("\nSample Section Box (Zone A, Section 1):")
    print(f"  {boxes['sections'][0]}")
    print("\nSample Shelf Box (Zone A, Section 1, Shelf 1):")
    print(f"  {boxes['shelves'][0]}")

if __name__ == "__main__":
    main()
