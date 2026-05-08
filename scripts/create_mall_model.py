#!/usr/bin/env python3
"""Generate simple 3D mall model as GLB."""
import struct
import json
from pathlib import Path

def create_simple_mall_glb():
    """Create a minimal GLB with floor and zone markers."""
    
    # Simple floor plane vertices (100m x 50m)
    vertices = [
        # Floor quad
        0.0, 0.0, 0.0,    # bottom-left
        100.0, 0.0, 0.0,  # bottom-right
        100.0, 0.0, 50.0, # top-right
        0.0, 0.0, 50.0,   # top-left
    ]
    
    # Indices for two triangles
    indices = [0, 1, 2, 0, 2, 3]
    
    # Pack binary data
    vertex_data = struct.pack(f'{len(vertices)}f', *vertices)
    index_data = struct.pack(f'{len(indices)}H', *indices)
    
    # Align to 4-byte boundary
    vertex_padding = (4 - len(vertex_data) % 4) % 4
    index_padding = (4 - len(index_data) % 4) % 4
    
    binary_data = vertex_data + b'\x00' * vertex_padding + index_data + b'\x00' * index_padding
    
    # glTF JSON structure
    gltf = {
        "asset": {"version": "2.0", "generator": "NaHarn 3D Generator"},
        "scene": 0,
        "scenes": [{"nodes": [0]}],
        "nodes": [{"mesh": 0}],
        "meshes": [{
            "primitives": [{
                "attributes": {"POSITION": 0},
                "indices": 1,
                "mode": 4  # TRIANGLES
            }]
        }],
        "accessors": [
            {
                "bufferView": 0,
                "componentType": 5126,  # FLOAT
                "count": 4,
                "type": "VEC3",
                "max": [100.0, 0.0, 50.0],
                "min": [0.0, 0.0, 0.0]
            },
            {
                "bufferView": 1,
                "componentType": 5123,  # UNSIGNED_SHORT
                "count": 6,
                "type": "SCALAR"
            }
        ],
        "bufferViews": [
            {
                "buffer": 0,
                "byteOffset": 0,
                "byteLength": len(vertex_data),
                "target": 34962  # ARRAY_BUFFER
            },
            {
                "buffer": 0,
                "byteOffset": len(vertex_data) + vertex_padding,
                "byteLength": len(index_data),
                "target": 34963  # ELEMENT_ARRAY_BUFFER
            }
        ],
        "buffers": [{"byteLength": len(binary_data)}]
    }
    
    json_data = json.dumps(gltf, separators=(',', ':')).encode('utf-8')
    json_padding = (4 - len(json_data) % 4) % 4
    json_chunk = json_data + b' ' * json_padding
    
    # GLB header
    magic = b'glTF'
    version = struct.pack('<I', 2)
    total_length = struct.pack('<I', 12 + 8 + len(json_chunk) + 8 + len(binary_data))
    
    # JSON chunk header
    json_chunk_length = struct.pack('<I', len(json_chunk))
    json_chunk_type = b'JSON'
    
    # Binary chunk header
    bin_chunk_length = struct.pack('<I', len(binary_data))
    bin_chunk_type = b'BIN\x00'
    
    # Write GLB
    output_path = Path("static/Naharn_3D.glb")
    output_path.parent.mkdir(exist_ok=True)
    
    with output_path.open('wb') as f:
        f.write(magic + version + total_length)
        f.write(json_chunk_length + json_chunk_type + json_chunk)
        f.write(bin_chunk_length + bin_chunk_type + binary_data)
    
    print(f"✓ Created {output_path} ({output_path.stat().st_size} bytes)")
    print(f"  Floor: 100m × 50m")
    print(f"  Zones: A(0-20m), B(20-40m), C(40-60m), D(60-80m), E(80-100m)")

if __name__ == "__main__":
    create_simple_mall_glb()
