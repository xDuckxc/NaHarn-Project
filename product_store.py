from __future__ import annotations

import json
import os
from typing import Any, Optional

from graph_state import SearchConstraints


PRODUCT_SELECT_COLUMNS = (
    "id,name,brand,category,description,price,stock_quantity,location_info"
)


def get_database_url() -> Optional[str]:
    return os.getenv("PRODUCT_DATABASE_URL") or os.getenv("DATABASE_URL") or os.getenv("SUPABASE_DB_DSN")


def use_supabase_backend() -> bool:
    backend = os.getenv("PRODUCT_BACKEND", "").strip().lower()
    if backend == "supabase":
        return True
    if backend == "postgres":
        return False
    return bool(os.getenv("SUPABASE_URL") and (os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_ANON_KEY")) and not get_database_url())


def vector_literal(vector: list[float]) -> str:
    return "[" + ",".join(format(float(value), ".9g") for value in vector) + "]"


def connect() -> Any:
    import psycopg

    database_url = get_database_url()
    if not database_url:
        raise RuntimeError("PRODUCT_DATABASE_URL is not set.")
    return psycopg.connect(database_url)


def run_schema_sql(schema_sql: str) -> None:
    with connect() as conn:
        conn.autocommit = True
        with conn.cursor() as cur:
            cur.execute(schema_sql)


def product_count(table: str) -> int:
    from psycopg import sql

    with connect() as conn:
        with conn.cursor() as cur:
            cur.execute(sql.SQL("select count(*) from {}").format(sql.Identifier(table)))
            return int(cur.fetchone()[0])


def upsert_products_postgres(table: str, rows: list[dict[str, Any]], batch_size: int) -> int:
    from psycopg import sql

    insert_sql = sql.SQL(
        """
        insert into {} (
            id, name, brand, category, description, embedding, price, stock_quantity, location_info
        )
        values (
            %s, %s, %s, %s, %s, %s::vector, %s, %s, %s::jsonb
        )
        on conflict (id) do update set
            name = excluded.name,
            brand = excluded.brand,
            category = excluded.category,
            description = excluded.description,
            embedding = excluded.embedding,
            price = excluded.price,
            stock_quantity = excluded.stock_quantity,
            location_info = excluded.location_info
        """
    ).format(sql.Identifier(table))

    total = 0
    with connect() as conn:
        with conn.cursor() as cur:
            for start in range(0, len(rows), batch_size):
                batch = rows[start : start + batch_size]
                values = [
                    (
                        row["id"],
                        row["name"],
                        row.get("brand"),
                        row["category"],
                        row.get("description"),
                        vector_literal(row["embedding"]),
                        row["price"],
                        row["stock_quantity"],
                        json.dumps(row["location_info"], ensure_ascii=False),
                    )
                    for row in batch
                ]
                cur.executemany(insert_sql, values)
                conn.commit()
                total += len(batch)
                print(f"Upserted {total}/{len(rows)} rows into local pgvector table {table}.")
    return total


def search_products_postgres(
    table: str,
    query_embedding: list[float],
    constraints: SearchConstraints,
    top_k: int,
    keyword: str,
) -> list[dict[str, Any]]:
    import psycopg
    from psycopg import sql

    vector = vector_literal(query_embedding)
    where_parts = [sql.SQL("true")]
    params: list[Any] = []

    if constraints.get("category"):
        where_parts.append(sql.SQL("category = %s"))
        params.append(constraints["category"])
    if constraints.get("min_price") is not None:
        where_parts.append(sql.SQL("price >= %s"))
        params.append(constraints["min_price"])
    if constraints.get("max_price") is not None:
        where_parts.append(sql.SQL("price <= %s"))
        params.append(constraints["max_price"])
    stock_status = constraints.get("stock_status")
    if stock_status == "out_of_stock":
        where_parts.append(sql.SQL("stock_quantity <= 0"))
    elif stock_status == "in_stock" or constraints.get("in_stock_only"):
        where_parts.append(sql.SQL("stock_quantity > 0"))
    if constraints.get("min_stock") is not None:
        where_parts.append(sql.SQL("stock_quantity >= %s"))
        params.append(int(constraints["min_stock"]))
    if constraints.get("max_stock") is not None:
        where_parts.append(sql.SQL("stock_quantity <= %s"))
        params.append(int(constraints["max_stock"]))

    query = sql.SQL(
        """
        select
            id,
            name,
            brand,
            category,
            description,
            price,
            stock_quantity,
            location_info,
            1 - (embedding <=> %s::vector) as similarity
        from {}
        where {}
        order by
            case
                when %s <> '' and (name ilike %s or brand ilike %s) then 0
                else 1
            end,
            embedding <=> %s::vector
        limit %s
        """
    ).format(
        sql.Identifier(table),
        sql.SQL(" and ").join(where_parts),
    )

    pattern = f"%{keyword}%"
    with connect() as conn:
        with conn.cursor(row_factory=psycopg.rows.dict_row) as cur:
            cur.execute(query, [vector, *params, keyword, pattern, pattern, vector, top_k])
            return list(cur.fetchall())


def fetch_products_by_ids_postgres(table: str, product_ids: list[int]) -> list[dict[str, Any]]:
    import psycopg
    from psycopg import sql

    if not product_ids:
        return []

    query = sql.SQL(
        """
        select id, name, brand, category, description, price, stock_quantity, location_info
        from {}
        where id = any(%s)
        """
    ).format(sql.Identifier(table))

    with connect() as conn:
        with conn.cursor(row_factory=psycopg.rows.dict_row) as cur:
            cur.execute(query, [sorted(set(int(product_id) for product_id in product_ids))])
            return list(cur.fetchall())
