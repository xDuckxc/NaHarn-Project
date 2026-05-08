from __future__ import annotations

import json
from collections import Counter
from dataclasses import dataclass
from typing import Any, Annotated, Literal, Optional

from langchain_core.messages import BaseMessage
from langchain_core.tools import tool
from langgraph.graph.message import add_messages
from typing_extensions import TypedDict


AllowedCategory = Literal[
    "อาหาร",
    "ของใช้ทั่วไป",
    "เสื้อผ้า",
    "เครื่องใช้ไฟฟ้า",
    "ยาสามัญ",
]

ALLOWED_CATEGORIES: tuple[str, ...] = (
    "อาหาร",
    "ของใช้ทั่วไป",
    "เสื้อผ้า",
    "เครื่องใช้ไฟฟ้า",
    "ยาสามัญ",
)

CATCHPHRASE = "หลงทางรึป่าว หาของไม่เจอใช่มั้ย"
NOT_FOUND_TEXT = "น้องหลงทางหาของไม่เจอครับ สินค้าน่าจะหมด"
OUT_OF_SCOPE_TEXT = (
    f"{CATCHPHRASE} เรื่องนี้อยู่นอกหน้าที่น้องครับ "
    "น้องหลงทางช่วยหาเฉพาะสินค้าในห้าง 5 หมวดนี้: "
    f"{', '.join(ALLOWED_CATEGORIES)}"
)
CLARIFY_CATEGORY_TEXT = (
    f"{CATCHPHRASE} น้องช่วยแนะนำสินค้าได้ครับ แต่ขอเลือกหมวดก่อนนะครับ: "
    f"{', '.join(ALLOWED_CATEGORIES)} "
    "เช่น `แนะนำอาหาร 10 อย่าง` หรือ `แนะนำของใช้ราคาไม่เกิน 50 บาท`"
)
PROMPT_INJECTION_TEXT = (
    f"{CATCHPHRASE} คำสั่งระบบของน้องยังเหมือนเดิมครับ "
    "น้องช่วยได้เฉพาะการหาสินค้าในห้าง และไม่สามารถเปลี่ยนบทบาทหรือเปิดเผยคำสั่งภายในได้"
)
SECURITY_REFUSAL_TEXT = (
    f"{CATCHPHRASE} เรื่องรหัสผ่าน การแฮก หรือการเลี่ยงระบบรักษาความปลอดภัย "
    "น้องช่วยไม่ได้ครับ น้องช่วยได้เฉพาะการหาสินค้าในห้างเท่านั้น"
)
HARMFUL_REFUSAL_TEXT = (
    f"{CATCHPHRASE} เรื่องวิธีทำอาวุธ ระเบิด หรือของอันตราย น้องช่วยไม่ได้ครับ "
    "ถ้าต้องการหาสินค้าปกติในห้าง บอกชื่อสินค้าหรือหมวดมาได้เลย"
)
EMERGENCY_TEXT = (
    "กรณีงูกัดหรือฉุกเฉินให้โทร 1669 ทันทีครับ ระหว่างรอความช่วยเหลือให้นั่งหรือนอนนิ่ง ๆ "
    "ถอดแหวน/นาฬิกา/ของรัดแน่นก่อนบวม ปิดแผลด้วยผ้าสะอาด และอย่ากรีดแผล ดูดพิษ ประคบน้ำแข็ง "
    "รัดขันชะเนาะ หรือดื่มแอลกอฮอล์ น้องหลงทางไม่ใช่แพทย์และไม่ควรใช้แทนหน่วยฉุกเฉินครับ"
)
UNSUPPORTED_ROUTE_TEXT = (
    f"{CATCHPHRASE} น้องจัดเส้นทางได้จากสินค้าในลิสต์ตามโซน A ถึง E เท่านั้นครับ "
    "ตอนนี้ข้อมูลห้างไม่มีชั้น 10 หรือดาดฟ้าในแผนที่สินค้า"
)
NEED_PRODUCT_ID_TEXT = (
    f"{CATCHPHRASE} ถ้าจะเพิ่มสินค้าลงลิสต์ ต้องใช้ ID จากตารางสินค้าครับ "
    "เช่น `เพิ่ม 12`, `เพิ่ม 4 80 6`, `เพิ่ม ID 12 จำนวน 2 ชิ้น`, `เพิ่มรายการที่ 2` หรือ `เพิ่มทั้งหมด`"
)


class Product(TypedDict, total=False):
    id: int
    name: str
    brand: str
    category: str
    description: str
    price: float
    stock_quantity: int
    location_info: dict[str, Any]
    similarity: float
    formatted_location: str


class SearchConstraints(TypedDict, total=False):
    category: Optional[str]
    min_price: Optional[float]
    max_price: Optional[float]
    min_stock: int
    max_stock: int
    in_stock_only: bool
    stock_status: Literal["in_stock", "out_of_stock"]
    stock_query: bool
    broad_category_query: bool
    diversify_results: bool
    max_results: int
    group_by: Literal["brand", "product"]


class MallState(TypedDict, total=False):
    messages: Annotated[list[BaseMessage], add_messages]
    shopping_list: list[int]
    current_context: str
    route: Literal["general", "search", "cart", "direct"]
    direct_response: str
    search_results: list[Product]
    validated_results: list[Product]
    constraints: SearchConstraints


@dataclass(frozen=True)
class RouteSummary:
    markdown: str
    total_price: float
    item_count: int


def normalize_category(raw_category: str) -> str:
    value = (raw_category or "").strip()
    if value in ALLOWED_CATEGORIES:
        return value

    prefix = value.split("/", 1)[0].strip()
    mapping = {
        "อาหาร": "อาหาร",
        "ของใช้": "ของใช้ทั่วไป",
        "เสื้อผ้า": "เสื้อผ้า",
        "ไฟฟ้า": "เครื่องใช้ไฟฟ้า",
        "เครื่องใช้ไฟฟ้า": "เครื่องใช้ไฟฟ้า",
        "ยา": "ยาสามัญ",
        "ยาสามัญ": "ยาสามัญ",
    }
    if prefix in mapping:
        return mapping[prefix]

    raise ValueError(
        f"Unsupported category {raw_category!r}. Allowed categories: {', '.join(ALLOWED_CATEGORIES)}"
    )


def parse_location_info(location_info: Any) -> dict[str, Any]:
    if isinstance(location_info, dict):
        return location_info
    if not location_info:
        return {}
    if isinstance(location_info, str):
        return json.loads(location_info)
    raise TypeError(f"location_info must be JSON string or dict, got {type(location_info)!r}")


def format_location(location_info: Any) -> str:
    info = parse_location_info(location_info)
    zone = str(info.get("zone", "-")).strip() or "-"
    section = str(info.get("section", "-")).strip() or "-"
    shelf = str(info.get("shelf", "")).strip()
    level = str(info.get("shelf_level", "")).strip()

    side_map = {
        "1": "ฝั่งขวามือ",
        "2": "ฝั่งขวามือ",
        "3": "ฝั่งขวามือ",
        "4": "ฝั่งซ้ายมือ",
        "5": "ฝั่งซ้ายมือ",
        "6": "ฝั่งซ้ายมือ",
    }
    level_map = {
        "1": "ชั้นล่างสุด",
        "2": "ระดับสายตา",
        "3": "ชั้นบนสุด",
    }

    side = side_map.get(shelf, f"ชั้นวาง {shelf}" if shelf else "ไม่ระบุฝั่ง")
    level_text = level_map.get(level, f"ระดับ {level}" if level else "ไม่ระบุระดับ")
    return f"โซน {zone} ล็อค {section} {side} {level_text}"


def product_sort_key(product: Product) -> tuple[str, int, int, int, str]:
    info = parse_location_info(product.get("location_info", {}))
    zone = str(info.get("zone", "Z")).upper()

    def to_int(value: Any, default: int = 999) -> int:
        try:
            return int(value)
        except (TypeError, ValueError):
            return default

    return (
        zone,
        to_int(info.get("section")),
        to_int(info.get("shelf")),
        to_int(info.get("shelf_level")),
        str(product.get("name", "")),
    )


def add_to_cart_state(shopping_list: Optional[list[int]], product_id: int) -> list[int]:
    updated = list(shopping_list or [])
    updated.append(int(product_id))
    return updated


@tool("add_to_cart")
def add_to_cart(product_id: int) -> str:
    """Return a tool instruction for adding a product ID to the LangGraph shopping_list state."""
    return f"ADD_TO_CART:{int(product_id)}"


@tool("summarize_route")
def summarize_route_tool() -> str:
    """Return a tool instruction for summarizing the current shopping route."""
    return "SUMMARIZE_ROUTE"


def summarize_route(products: list[Product], shopping_list: list[int]) -> RouteSummary:
    if not shopping_list:
        return RouteSummary(
            markdown=(
                f"{CATCHPHRASE} ตอนนี้ลิสต์ยังว่างอยู่ครับ "
                "บอกน้องหลงทางได้เลยว่าอยากหาอะไร"
            ),
            total_price=0.0,
            item_count=0,
        )

    counts = Counter(int(pid) for pid in shopping_list)
    products_by_id = {int(product["id"]): product for product in products if "id" in product}
    route_products = [products_by_id[pid] for pid in counts if pid in products_by_id]
    route_products.sort(key=product_sort_key)

    missing_ids = [pid for pid in counts if pid not in products_by_id]
    total = 0.0
    rows = [
        "| ลำดับ | สินค้า | จำนวน | ตำแหน่งเดินหา | ราคา/ชิ้น | รวม |",
        "|---:|---|---:|---|---:|---:|",
    ]

    for idx, product in enumerate(route_products, start=1):
        pid = int(product["id"])
        qty = counts[pid]
        price = float(product.get("price") or 0.0)
        line_total = price * qty
        total += line_total
        location = product.get("formatted_location") or format_location(product.get("location_info", {}))
        rows.append(
            f"| {idx} | {product.get('name', '-')} | {qty} | {location} | "
            f"{price:,.2f} | {line_total:,.2f} |"
        )

    if missing_ids:
        rows.append(
            f"\n> หมายเหตุ: ไม่พบสินค้า ID {', '.join(map(str, missing_ids))} ในฐานข้อมูลปัจจุบัน"
        )

    markdown = (
        f"{CATCHPHRASE} น้องหลงทางจัดเส้นทางเดินให้แล้วครับ เริ่มจากโซน A ไปต่อถึงโซน E ตามลำดับ\n\n"
        + "\n".join(rows)
        + f"\n\n**รวมทั้งหมด: {total:,.2f} บาท**"
    )
    return RouteSummary(markdown=markdown, total_price=total, item_count=sum(counts.values()))
