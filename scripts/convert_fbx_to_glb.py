#!/usr/bin/env python3
"""Convert FBX to GLB using Blender."""
import bpy
import sys

# Clear scene
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete()

# Import FBX (skip lights to avoid compatibility issues)
fbx_path = "Naharn_3D.fbx"
bpy.ops.import_scene.fbx(
    filepath=fbx_path,
    use_custom_props=True,
    use_image_search=True,
    ignore_leaf_bones=False,
    force_connect_children=False,
    automatic_bone_orientation=False,
    primary_bone_axis='Y',
    secondary_bone_axis='X',
    use_prepost_rot=True
)

# Export GLB
glb_path = "static/Naharn_3D.glb"
bpy.ops.export_scene.gltf(
    filepath=glb_path,
    export_format='GLB',
    export_texcoords=True,
    export_normals=True,
    export_materials='EXPORT',
    export_colors=True,
    export_cameras=False,
    export_lights=False
)

print(f"Converted {fbx_path} -> {glb_path}")
