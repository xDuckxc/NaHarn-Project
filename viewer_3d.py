"""Helper functions for 3D viewer integration."""
import json
from typing import Any


def generate_3d_viewer_script(products: list[dict[str, Any]]) -> str:
    """Generate JavaScript to display products in 3D viewer."""
    pins = []
    for product in products:
        coords = product.get("coordinates_3d", {})
        if not coords or not all(k in coords for k in ("x", "y", "z")):
            continue
        pins.append({
            "id": product.get("id"),
            "name": product.get("name", ""),
            "x": coords["x"],
            "y": coords["y"],
            "z": coords["z"]
        })
    
    if not pins:
        return ""
    
    script = f"""
<script>
// Send product coordinates to 3D viewer (if open in another tab)
const products3D = {json.dumps(pins, ensure_ascii=False)};
if (window.opener && window.opener.mall3D) {{
    window.opener.mall3D.clearPins();
    products3D.forEach(p => {{
        window.opener.mall3D.addPin(p.id, p.x, p.y, p.z, p.name);
    }});
    if (products3D.length > 0) {{
        const first = products3D[0];
        window.opener.mall3D.focusOn(first.x, first.y, first.z);
    }}
}}
console.log('3D coordinates ready:', products3D.length, 'products');
</script>
"""
    return script


def format_3d_viewer_link(product_count: int = 0) -> str:
    """Format link to 3D viewer with product count."""
    if product_count > 0:
        return f"\n\n🗺️ **[ดูตำแหน่งใน 3D Navigator](/public/model_viewer.html)** ({product_count} รายการ)"
    return "\n\n🗺️ **[เปิด 3D Navigator](/public/model_viewer.html)**"
