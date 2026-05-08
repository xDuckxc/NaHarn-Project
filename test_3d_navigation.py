#!/usr/bin/env python3
"""Test 3D navigation system."""
import json
import sys
sys.path.insert(0, '/Users/ayo/Desktop/AIE322/NaHarn-Project')

from product_store import connect

def test_3d_coordinates():
    """Test that products have valid 3D coordinates."""
    with connect() as conn:
        with conn.cursor() as cur:
            # Check total products with coordinates
            cur.execute("SELECT COUNT(*) FROM products WHERE coordinates_3d IS NOT NULL")
            total = cur.fetchone()[0]
            print(f"✓ Products with 3D coordinates: {total}")
            
            # Check coordinate ranges
            cur.execute("""
                SELECT 
                    MIN((coordinates_3d->>'x')::float) as min_x,
                    MAX((coordinates_3d->>'x')::float) as max_x,
                    MIN((coordinates_3d->>'y')::float) as min_y,
                    MAX((coordinates_3d->>'y')::float) as max_y,
                    MIN((coordinates_3d->>'z')::float) as min_z,
                    MAX((coordinates_3d->>'z')::float) as max_z
                FROM products
                WHERE coordinates_3d IS NOT NULL
            """)
            ranges = cur.fetchone()
            print(f"✓ X range: {ranges[0]:.1f} to {ranges[1]:.1f}m")
            print(f"✓ Y range: {ranges[2]:.1f} to {ranges[3]:.1f}m")
            print(f"✓ Z range: {ranges[4]:.1f} to {ranges[5]:.1f}m")
            
            # Sample products by zone
            cur.execute("""
                SELECT 
                    location_info->>'zone' as zone,
                    COUNT(*) as count
                FROM products
                GROUP BY zone
                ORDER BY zone
            """)
            zones = cur.fetchall()
            print("\n✓ Products by zone:")
            for zone, count in zones:
                print(f"  Zone {zone}: {count} products")
            
            # Sample product with full details
            cur.execute("""
                SELECT id, name, location_info, coordinates_3d
                FROM products
                WHERE coordinates_3d IS NOT NULL
                LIMIT 1
            """)
            sample = cur.fetchone()
            print(f"\n✓ Sample product:")
            print(f"  ID: {sample[0]}")
            print(f"  Name: {sample[1]}")
            print(f"  Location: {json.dumps(sample[2], ensure_ascii=False)}")
            print(f"  3D Coords: {json.dumps(sample[3], ensure_ascii=False)}")

if __name__ == "__main__":
    test_3d_coordinates()
