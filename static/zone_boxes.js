
// Zone bounding boxes for 3D visualization
const zoneBoxes = [
  {
    zone: "A",
    color: "#FF6B6B",
    position: { x: 10.0, y: 2.0, z: 25.0 },
    size: { width: 20.0, height: 4.0, depth: 50.0 },
    bounds: {
      min: { x: 0.0, y: 0.0, z: 0.0 },
      max: { x: 20.0, y: 4.0, z: 50.0 }
    }
  },
  {
    zone: "B",
    color: "#4ECDC4",
    position: { x: 30.0, y: 2.0, z: 25.0 },
    size: { width: 20.0, height: 4.0, depth: 50.0 },
    bounds: {
      min: { x: 20.0, y: 0.0, z: 0.0 },
      max: { x: 40.0, y: 4.0, z: 50.0 }
    }
  },
  {
    zone: "C",
    color: "#45B7D1",
    position: { x: 50.0, y: 2.0, z: 25.0 },
    size: { width: 20.0, height: 4.0, depth: 50.0 },
    bounds: {
      min: { x: 40.0, y: 0.0, z: 0.0 },
      max: { x: 60.0, y: 4.0, z: 50.0 }
    }
  },
  {
    zone: "D",
    color: "#FFA07A",
    position: { x: 70.0, y: 2.0, z: 25.0 },
    size: { width: 20.0, height: 4.0, depth: 50.0 },
    bounds: {
      min: { x: 60.0, y: 0.0, z: 0.0 },
      max: { x: 80.0, y: 4.0, z: 50.0 }
    }
  },
  {
    zone: "E",
    color: "#98D8C8",
    position: { x: 90.0, y: 2.0, z: 25.0 },
    size: { width: 20.0, height: 4.0, depth: 50.0 },
    bounds: {
      min: { x: 80.0, y: 0.0, z: 0.0 },
      max: { x: 100.0, y: 4.0, z: 50.0 }
    }
  },
];

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
