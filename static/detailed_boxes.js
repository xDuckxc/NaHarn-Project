
// Detailed bounding boxes (sections and shelves)
const detailedBoxes = {
    sections: [
        { zone: 'A', section: 1, x: 10.0, y: 2.0, z: 1.5, w: 20.0, h: 4.0, d: 3.0, color: 0x888888 },
        { zone: 'A', section: 2, x: 10.0, y: 2.0, z: 4.5, w: 20.0, h: 4.0, d: 3.0, color: 0x888888 },
        { zone: 'A', section: 3, x: 10.0, y: 2.0, z: 7.5, w: 20.0, h: 4.0, d: 3.0, color: 0x888888 },
        { zone: 'A', section: 4, x: 10.0, y: 2.0, z: 10.5, w: 20.0, h: 4.0, d: 3.0, color: 0x888888 },
        { zone: 'A', section: 5, x: 10.0, y: 2.0, z: 13.5, w: 20.0, h: 4.0, d: 3.0, color: 0x888888 },
        { zone: 'B', section: 1, x: 30.0, y: 2.0, z: 1.5, w: 20.0, h: 4.0, d: 3.0, color: 0x888888 },
        { zone: 'B', section: 2, x: 30.0, y: 2.0, z: 4.5, w: 20.0, h: 4.0, d: 3.0, color: 0x888888 },
        { zone: 'B', section: 3, x: 30.0, y: 2.0, z: 7.5, w: 20.0, h: 4.0, d: 3.0, color: 0x888888 },
        { zone: 'B', section: 4, x: 30.0, y: 2.0, z: 10.5, w: 20.0, h: 4.0, d: 3.0, color: 0x888888 },
        { zone: 'B', section: 5, x: 30.0, y: 2.0, z: 13.5, w: 20.0, h: 4.0, d: 3.0, color: 0x888888 },
        { zone: 'C', section: 1, x: 50.0, y: 2.0, z: 1.5, w: 20.0, h: 4.0, d: 3.0, color: 0x888888 },
        { zone: 'C', section: 2, x: 50.0, y: 2.0, z: 4.5, w: 20.0, h: 4.0, d: 3.0, color: 0x888888 },
        { zone: 'C', section: 3, x: 50.0, y: 2.0, z: 7.5, w: 20.0, h: 4.0, d: 3.0, color: 0x888888 },
        { zone: 'C', section: 4, x: 50.0, y: 2.0, z: 10.5, w: 20.0, h: 4.0, d: 3.0, color: 0x888888 },
        { zone: 'C', section: 5, x: 50.0, y: 2.0, z: 13.5, w: 20.0, h: 4.0, d: 3.0, color: 0x888888 },
        { zone: 'D', section: 1, x: 70.0, y: 2.0, z: 1.5, w: 20.0, h: 4.0, d: 3.0, color: 0x888888 },
        { zone: 'D', section: 2, x: 70.0, y: 2.0, z: 4.5, w: 20.0, h: 4.0, d: 3.0, color: 0x888888 },
        { zone: 'D', section: 3, x: 70.0, y: 2.0, z: 7.5, w: 20.0, h: 4.0, d: 3.0, color: 0x888888 },
        { zone: 'D', section: 4, x: 70.0, y: 2.0, z: 10.5, w: 20.0, h: 4.0, d: 3.0, color: 0x888888 },
        { zone: 'D', section: 5, x: 70.0, y: 2.0, z: 13.5, w: 20.0, h: 4.0, d: 3.0, color: 0x888888 },
        { zone: 'E', section: 1, x: 90.0, y: 2.0, z: 1.5, w: 20.0, h: 4.0, d: 3.0, color: 0x888888 },
        { zone: 'E', section: 2, x: 90.0, y: 2.0, z: 4.5, w: 20.0, h: 4.0, d: 3.0, color: 0x888888 },
        { zone: 'E', section: 3, x: 90.0, y: 2.0, z: 7.5, w: 20.0, h: 4.0, d: 3.0, color: 0x888888 },
        { zone: 'E', section: 4, x: 90.0, y: 2.0, z: 10.5, w: 20.0, h: 4.0, d: 3.0, color: 0x888888 },
        { zone: 'E', section: 5, x: 90.0, y: 2.0, z: 13.5, w: 20.0, h: 4.0, d: 3.0, color: 0x888888 },
    ],
    shelves: [
        { zone: 'A', section: 1, shelf: 1, x: 2.25, y: 2.0, z: 1.5, w: 2.5, h: 4.0, d: 0.8, color: 0xff00 },
        { zone: 'A', section: 1, shelf: 2, x: 4.75, y: 2.0, z: 1.5, w: 2.5, h: 4.0, d: 0.8, color: 0xff00 },
        { zone: 'A', section: 1, shelf: 3, x: 7.25, y: 2.0, z: 1.5, w: 2.5, h: 4.0, d: 0.8, color: 0xff00 },
        { zone: 'A', section: 1, shelf: 4, x: 12.75, y: 2.0, z: 1.5, w: 2.5, h: 4.0, d: 0.8, color: 0xff },
        { zone: 'A', section: 1, shelf: 5, x: 10.25, y: 2.0, z: 1.5, w: 2.5, h: 4.0, d: 0.8, color: 0xff },
        { zone: 'A', section: 1, shelf: 6, x: 7.75, y: 2.0, z: 1.5, w: 2.5, h: 4.0, d: 0.8, color: 0xff },
    ]
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
