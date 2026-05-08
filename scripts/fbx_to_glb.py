#!/usr/bin/env python3
"""Convert FBX to GLB using trimesh."""
import trimesh

# Load FBX
scene = trimesh.load("Naharn_3D.fbx")

# Export as GLB
scene.export("static/Naharn_3D.glb", file_type="glb")

print("✓ Converted Naharn_3D.fbx → static/Naharn_3D.glb")
