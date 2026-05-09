from __future__ import annotations

import argparse
import csv
import json
import os
from pathlib import Path
from typing import Any, Iterable

from dotenv import load_dotenv

from naharn.graph_state import ALLOWED_CATEGORIES, format_location, normalize_category, parse_location_info
from naharn.paths import DATA_DIR, PROJECT_ROOT
from naharn.product_store import (
    get_database_url,
    product_count,
    run_schema_sql as run_postgres_schema_sql,
    upsert_products_postgres,
    use_supabase_backend,
)


DEFAULT_CSV_PATH = str(DATA_DIR / "mall_products_500_with_3d.csv")
DEFAULT_EMBEDDING_MODEL = "intfloat/multilingual-e5-large"
DEFAULT_TABLE = "products"

CREATE_SCHEMA_SQL = """
create extension if not exists vector;

create table if not exists products (
    id integer primary key,
    name text not null,
    brand text,
    category text not null check (
        category in ('อาหาร', 'ของใช้ทั่วไป', 'เสื้อผ้า', 'เครื่องใช้ไฟฟ้า', 'ยาสามัญ')
    ),
    description text,
    embedding vector(1024) not null,
    price double precision not null check (price >= 0),
    stock_quantity integer not null check (stock_quantity >= 0),
    location_info jsonb not null,
    coordinates_3d jsonb
);

create index if not exists products_category_idx on products (category);
create index if not exists products_price_idx on products (price);
create index if not exists products_stock_idx on products (stock_quantity);
create index if not exists products_location_zone_idx
    on products ((location_info->>'zone'));
create index if not exists products_text_search_idx
    on products using gin (
        to_tsvector('simple', coalesce(name, '') || ' ' || coalesce(brand, '') || ' ' || coalesce(description, ''))
    );
create index if not exists products_embedding_hnsw_idx
    on products using hnsw (embedding vector_cosine_ops);

create or replace function match_products(
    query_embedding vector(1024),
    match_count integer default 8,
    filter_category text default null,
    min_price double precision default null,
    max_price double precision default null,
    in_stock_only boolean default false,
    keyword text default null
)
returns table (
    id integer,
    name text,
    brand text,
    category text,
    description text,
    price double precision,
    stock_quantity integer,
    location_info jsonb,
    coordinates_3d jsonb,
    similarity double precision
)
language sql
stable
as $$
    select
        p.id,
        p.name,
        p.brand,
        p.category,
        p.description,
        p.price,
        p.stock_quantity,
        p.location_info,
        p.coordinates_3d,
        1 - (p.embedding <=> query_embedding) as similarity
    from products p
    where
        (filter_category is null or p.category = filter_category)
        and (min_price is null or p.price >= min_price)
        and (max_price is null or p.price <= max_price)
        and (not in_stock_only or p.stock_quantity > 0)
    order by
        p.embedding <=> query_embedding,
        case
            when keyword is not null and keyword <> '' and (
                p.name ilike '%' || keyword || '%'
                or p.brand ilike '%' || keyword || '%'
            ) then 0
            else 1
        end
    limit match_count;
$$;
"""


def get_supabase_client() -> Any:
    from supabase import create_client

    load_dotenv(PROJECT_ROOT / ".env")
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_ANON_KEY")
    if not url or not key:
        raise RuntimeError("Set SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY or SUPABASE_ANON_KEY.")
    return create_client(url, key)


def coerce_product_id(raw_id: str, row_number: int) -> int:
    try:
        return int(str(raw_id).strip())
    except (TypeError, ValueError):
        return row_number


def product_text_for_embedding(row: dict[str, Any]) -> str:
    location_text = format_location(row.get("location_info", {}))
    return (
        f"passage: สินค้า {row['name']} แบรนด์ {row.get('brand') or '-'} "
        f"หมวด {row['category']} รายละเอียด {row.get('description') or ''} "
        f"ราคา {row['price']} บาท ตำแหน่ง {location_text}"
    )


def batched(items: list[dict[str, Any]], batch_size: int) -> Iterable[list[dict[str, Any]]]:
    for start in range(0, len(items), batch_size):
        yield items[start : start + batch_size]


def load_csv_rows(csv_path: Path) -> list[dict[str, Any]]:
    if not csv_path.exists():
        raise FileNotFoundError(f"CSV file not found: {csv_path}")

    rows: list[dict[str, Any]] = []
    with csv_path.open(newline="", encoding="utf-8-sig") as file:
        reader = csv.DictReader(file)
        required = {"id", "name", "brand", "category", "description", "price", "stock_quantity", "location_info"}
        missing = required - set(reader.fieldnames or [])
        if missing:
            raise ValueError(f"CSV missing required columns: {', '.join(sorted(missing))}")

        for row_number, row in enumerate(reader, start=1):
            category = normalize_category(row["category"])
            location = parse_location_info(row["location_info"])
            coordinates_3d = parse_location_info(row.get("coordinates_3d", "{}"))
            rows.append(
                {
                    "id": coerce_product_id(row.get("id", ""), row_number),
                    "name": row["name"].strip(),
                    "brand": (row.get("brand") or "").strip(),
                    "category": category,
                    "description": (row.get("description") or "").strip(),
                    "price": float(row["price"]),
                    "stock_quantity": int(float(row["stock_quantity"])),
                    "location_info": location,
                    "coordinates_3d": coordinates_3d,
                }
            )
    return rows


def embed_rows(rows: list[dict[str, Any]], model_name: str, batch_size: int) -> list[dict[str, Any]]:
    from sentence_transformers import SentenceTransformer

    model = SentenceTransformer(model_name)
    texts = [product_text_for_embedding(row) for row in rows]
    vectors = model.encode(
        texts,
        batch_size=batch_size,
        normalize_embeddings=True,
        show_progress_bar=True,
    )

    embedded: list[dict[str, Any]] = []
    for row, vector in zip(rows, vectors, strict=True):
        record = dict(row)
        record["embedding"] = [float(value) for value in vector]
        embedded.append(record)
    return embedded


def upsert_products(client: Any, table: str, rows: list[dict[str, Any]], batch_size: int) -> int:
    total = 0
    for batch in batched(rows, batch_size):
        client.table(table).upsert(batch, on_conflict="id").execute()
        total += len(batch)
        print(f"Upserted {total}/{len(rows)} rows into {table}.")
    return total


def should_skip_load(table: str, expected_rows: int) -> bool:
    if use_supabase_backend():
        return False
    try:
        current_count = product_count(table)
    except Exception:
        return False
    if current_count >= expected_rows:
        print(f"Skipping embedding/load: {table} already has {current_count} rows.")
        return True
    return False


def main() -> None:
    parser = argparse.ArgumentParser(description="Load mall products into pgvector.")
    parser.add_argument("--csv", default=DEFAULT_CSV_PATH, help="Path to mall_products_500_with_3d.csv.")
    parser.add_argument("--table", default=os.getenv("PRODUCT_TABLE", DEFAULT_TABLE))
    parser.add_argument("--model", default=os.getenv("EMBEDDING_MODEL", DEFAULT_EMBEDDING_MODEL))
    parser.add_argument("--embed-batch-size", type=int, default=32)
    parser.add_argument("--upsert-batch-size", type=int, default=25)
    parser.add_argument("--init-db", action="store_true", help="Run pgvector/table/function SQL via PRODUCT_DATABASE_URL.")
    parser.add_argument("--print-sql", action="store_true", help="Print the table and RPC SQL, then exit.")
    parser.add_argument("--skip-if-loaded", action="store_true", help="Skip embedding if the table already has the CSV row count.")
    args = parser.parse_args()

    load_dotenv(PROJECT_ROOT / ".env")

    if args.print_sql:
        print(CREATE_SCHEMA_SQL)
        return

    if args.init_db:
        if not get_database_url():
            raise RuntimeError("PRODUCT_DATABASE_URL is required for automatic local database initialization.")
        run_postgres_schema_sql(CREATE_SCHEMA_SQL)
        print("Schema initialized with pgvector table, indexes, and match_products RPC.")

    rows = load_csv_rows(Path(args.csv))
    categories = sorted({row["category"] for row in rows})
    invalid = set(categories) - set(ALLOWED_CATEGORIES)
    if invalid:
        raise ValueError(f"Invalid normalized categories: {json.dumps(sorted(invalid), ensure_ascii=False)}")

    if args.skip_if_loaded and should_skip_load(args.table, len(rows)):
        return

    embedded_rows = embed_rows(rows, args.model, args.embed_batch_size)
    if use_supabase_backend():
        client = get_supabase_client()
        count = upsert_products(client, args.table, embedded_rows, args.upsert_batch_size)
    else:
        count = upsert_products_postgres(args.table, embedded_rows, args.upsert_batch_size)
    print(f"Done. Loaded {count} real products from {args.csv}.")


if __name__ == "__main__":
    main()
