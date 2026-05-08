#!/usr/bin/env python3
"""Generate zone box geometries for Three.js visualization."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from zone_volumes import generate_all_zone_volumes, ZONE_CONFIGS

def generate_threejs_zone_boxes():
    """Generate JavaScript code for zone boxes in Three.js."""
    volumes = generate_all_zone_volumes()
    
    js_code = """
// Zone bounding boxes for 3D visualization
const zoneBoxes = [
"""
    
    for zone, data in volumes.items():
        vol = data["volume"]
        color = data["color"]
        
        js_code += f"""  {{
    zone: "{zone}",
    color: "{color}",
    position: {{ x: {vol['center_x']}, y: {vol['center_y']}, z: {vol['center_z']} }},
    size: {{ width: {vol['width']}, height: {vol['height']}, depth: {vol['depth']} }},
    bounds: {{
      min: {{ x: {vol['min_x']}, y: {vol['min_y']}, z: {vol['min_z']} }},
      max: {{ x: {vol['max_x']}, y: {vol['max_y']}, z: {vol['max_z']} }}
    }}
  }},
"""
    
    js_code += """];

// Create zone box meshes
function createZoneBoxes(scene) {
  const boxes = [];
  
  zoneBoxes.forEach(zoneData => {
    // Create box geometry
    const geometry = new THREE.BoxGeometry(
      zoneData.size.width,
      zoneData.size.height,
      zoneData.size.depth
    );
    
    // Wireframe edges only (dev mode)
    const edges = new THREE.EdgesGeometry(geometry);
    const lineMaterial = new THREE.LineBasicMaterial({
      color: zoneData.color,
      linewidth: 2
    });
    const wireframe = new THREE.LineSegments(edges, lineMaterial);
    wireframe.position.set(
      zoneData.position.x,
      zoneData.position.y,
      zoneData.position.z
    );
    
    wireframe.userData = { zone: zoneData.zone };
    scene.add(wireframe);
    boxes.push(wireframe);
  });
  
  return boxes;
}

// Export for use in model_viewer.html
if (typeof module !== 'undefined' && module.exports) {
  module.exports = { zoneBoxes, createZoneBoxes };
}
"""
    
    return js_code

def main():
    output_path = Path("static/zone_boxes.js")
    output_path.parent.mkdir(exist_ok=True)
    
    js_code = generate_threejs_zone_boxes()
    output_path.write_text(js_code, encoding="utf-8")
    
    print(f"✓ Generated {output_path}")
    print(f"✓ Zone boxes: {len(ZONE_CONFIGS)}")
    
    # Also copy to public
    public_path = Path("public/zone_boxes.js")
    public_path.write_text(js_code, encoding="utf-8")
    print(f"✓ Copied to {public_path}")

if __name__ == "__main__":
    main()
