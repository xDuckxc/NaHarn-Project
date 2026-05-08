from __future__ import annotations

import asyncio
import inspect
import json
import os
import re
import unicodedata
from functools import lru_cache
from typing import Any, Iterable, Optional

from dotenv import load_dotenv
from langchain_core.messages import AIMessage, HumanMessage
from langchain_core.runnables import RunnableConfig
from openai import AsyncOpenAI
from sentence_transformers import SentenceTransformer

from graph_state import (
    ALLOWED_CATEGORIES,
    CATCHPHRASE,
    CLARIFY_CATEGORY_TEXT,
    EMERGENCY_TEXT,
    HARMFUL_REFUSAL_TEXT,
    NEED_PRODUCT_ID_TEXT,
    NOT_FOUND_TEXT,
    MallState,
    OUT_OF_SCOPE_TEXT,
    PROMPT_INJECTION_TEXT,
    Product,
    SearchConstraints,
    SECURITY_REFUSAL_TEXT,
    UNSUPPORTED_ROUTE_TEXT,
    add_to_cart_state,
    format_location,
    normalize_category,
    parse_location_info,
    summarize_route,
)
from product_store import (
    fetch_products_by_ids_postgres,
    search_products_postgres,
    use_supabase_backend,
)

try:
    from langgraph.checkpoint.memory import MemorySaver
except ImportError:  # pragma: no cover - compatibility with newer LangGraph naming
    from langgraph.checkpoint.memory import InMemorySaver as MemorySaver

from langgraph.graph import END, START, StateGraph


load_dotenv()

SUPERVISOR_GUARDRAIL_PROMPT = (
    "You are น้องหลงทาง. You only assist with finding items in the mall (5 categories). "
    "NEVER hallucinate product names. If info is not in the context, say "
    "'น้องหลงทางหาของไม่เจอครับ สินค้าน่าจะหมด'."
)

PRODUCT_SELECT_COLUMNS = (
    "id,name,brand,category,description,price,stock_quantity,location_info,coordinates_3d"
)

THAI_CATEGORY_KEYWORDS: dict[str, str] = {
    "อาหาร": "อาหาร",
    "ของกิน": "อาหาร",
    "ขนม": "อาหาร",
    "ข้าวสวย": "อาหาร",
    "ข้าวสาร": "อาหาร",
    "ข้าว": "อาหาร",
    "เนื้อสัตว์": "อาหาร",
    "กับข้าว": "อาหาร",
    "มาม่า": "อาหาร",
    "โจ๊ก": "อาหาร",
    "น้ำดื่ม": "อาหาร",
    "น้ำอัดลม": "อาหาร",
    "มันฝรั่ง": "อาหาร",
    "มันฝรั่งทอด": "อาหาร",
    "เครื่องดื่ม": "อาหาร",
    "เบเกอรี่": "อาหาร",
    "เครื่องปรุง": "อาหาร",
    "ของใช้": "ของใช้ทั่วไป",
    "ของใช้ทั่วไป": "ของใช้ทั่วไป",
    "ของใช้ในบ้าน": "ของใช้ทั่วไป",
    "แชมพู": "ของใช้ทั่วไป",
    "สบู่": "ของใช้ทั่วไป",
    "ยาสีฟัน": "ของใช้ทั่วไป",
    "แปรงสีฟัน": "ของใช้ทั่วไป",
    "น้ำยาล้างจาน": "ของใช้ทั่วไป",
    "น้ำยาซักผ้า": "ของใช้ทั่วไป",
    "ซักล้าง": "ของใช้ทั่วไป",
    "ทำความสะอาด": "ของใช้ทั่วไป",
    "เสื้อ": "เสื้อผ้า",
    "กางเกง": "เสื้อผ้า",
    "กระโปรง": "เสื้อผ้า",
    "เครื่องประดับ": "เสื้อผ้า",
    "ไฟฟ้า": "เครื่องใช้ไฟฟ้า",
    "เครื่องใช้ไฟฟ้า": "เครื่องใช้ไฟฟ้า",
    "มือถือ": "เครื่องใช้ไฟฟ้า",
    "ไอที": "เครื่องใช้ไฟฟ้า",
    "ทีวี": "เครื่องใช้ไฟฟ้า",
    "โทรทัศน์": "เครื่องใช้ไฟฟ้า",
    "หม้อหุง": "เครื่องใช้ไฟฟ้า",
    "ไมโครเวฟ": "เครื่องใช้ไฟฟ้า",
    "หม้อทอด": "เครื่องใช้ไฟฟ้า",
    "หูฟัง": "เครื่องใช้ไฟฟ้า",
    "พัดลม": "เครื่องใช้ไฟฟ้า",
    "ยาแก้": "ยาสามัญ",
    "ยา": "ยาสามัญ",
    "วิตามิน": "ยาสามัญ",
    "แก้ปวด": "ยาสามัญ",
    "แก้หวัด": "ยาสามัญ",
    "ปฐมพยาบาล": "ยาสามัญ",
}

TERM_SYNONYMS: dict[str, tuple[str, ...]] = {
    "ขนม": ("เลย์", "ทาโร่", "ป๊อกกี้", "ฮานามิ", "สแน็คแจ๊ค", "เค้ก", "โดนัท", "ครัวซองต์", "ขนมปัง"),
    "เนื้อสัตว์": ("หมู", "ปลากระป๋อง", "แฮม", "กุ้ง", "เนื้อ"),
    "เนื้อ": ("หมู", "ปลากระป๋อง", "แฮม", "กุ้ง", "เนื้อ"),
    "ของคาว": ("ข้าว", "โจ๊ก", "มาม่า", "ปลา", "แซนวิช"),
    "ข้าว": ("ข้าว", "โจ๊ก", "กับข้าว"),
}

SPECIFIC_PRODUCT_TYPE_KEYWORDS: tuple[str, ...] = (
    "ขนม",
    "เนื้อสัตว์",
    "เนื้อ",
    "ของคาว",
    "กับข้าว",
    "มาม่า",
    "โจ๊ก",
    "ข้าว",
    "ข้าวสาร",
    "ข้าวสวย",
    "น้ำดื่ม",
    "น้ำอัดลม",
    "เครื่องดื่ม",
    "มันฝรั่ง",
    "เบเกอรี่",
    "เครื่องปรุง",
)

THAI_NUMBER_WORDS: dict[str, int] = {
    "หนึ่ง": 1,
    "สอง": 2,
    "สาม": 3,
    "สี่": 4,
    "ห้า": 5,
    "หก": 6,
    "เจ็ด": 7,
    "แปด": 8,
    "เก้า": 9,
    "สิบ": 10,
}

PROMPT_INJECTION_PATTERNS: tuple[str, ...] = (
    r"ignore\s+(?:all\s+)?(?:(?:previous|prior|above)\s+)?(?:instructions?|directives?|rules?)",
    r"disregard\s+(?:(?:previous|prior|above)\s+)?(?:instructions?|directives?|rules?)",
    r"print\s+out\s+.*system\s+prompt",
    r"print\s+rules?",
    r"initial\s+system\s+prompt",
    r"system\s+(?:prompt|message|instruction)",
    r"developer\s+(?:prompt|message|instruction)",
    r"you\s+are\s+now",
    r"uncensored\s+assistant",
    r"jailbreak",
    r"\bdan\b",
    r"ลืมคำสั่ง",
    r"คำสั่งก่อนหน้า",
    r"คำสั่งระบบ",
    r"สรุปคำสั่ง",
    r"เปิดเผย.*(?:prompt|พรอมป์|คำสั่ง)",
    r"ห้ามพูด",
    r"ตอนนี้คุณคือ",
    r"เปลี่ยนบทบาท",
    r"ข้ามกฎ",
    r"ข้ามกติกา",
)

PROMPT_INJECTION_COMPACT_PATTERNS: tuple[str, ...] = (
    r"ignoreinstructions",
    r"ignorepreviousinstructions",
    r"disregardinstructions",
    r"printrules",
    r"systemprompt",
    r"youarenow",
    r"uncensoredassistant",
    r"ลืมคำสั่ง",
    r"คำสั่งระบบ",
    r"สรุปคำสั่ง",
    r"เปิดเผยคำสั่ง",
    r"ตอนนี้คุณคือ",
    r"ข้ามกฎ",
)

CODING_OUT_OF_DOMAIN_PATTERNS: tuple[str, ...] = (
    r"\bpython\b",
    r"\bfibonacci\b",
    r"\bjavascript\b",
    r"\bsql\b",
    r"เขียนโค้ด",
    r"โค้ด",
    r"ฟังก์ชัน",
    r"เขียนโปรแกรม",
)

FINANCE_OUT_OF_DOMAIN_PATTERNS: tuple[str, ...] = (
    r"ยืมเงิน",
    r"เงินช็อต",
    r"สินเชื่อ",
    r"ปล่อยกู้",
    r"กู้เงิน",
    r"ดอกเบี้ย",
    r"ผ่อนจ่าย",
)

OUTSIDE_MALL_PATTERNS: tuple[str, ...] = (
    r"หน้าปากซอย",
    r"นอกห้าง",
    r"ข้างนอกห้าง",
    r"ไม่อยากกินของในห้าง",
    r"ร้านอาหารตามสั่ง",
)

ROLEPLAY_OUT_OF_DOMAIN_PATTERNS: tuple[str, ...] = (
    r"ถ้า(?:นาย|คุณ|น้อง).*เป็น",
    r"สมมติว่า",
    r"เล่นเกม",
    r"\brpg\b",
    r"ไม่ใช่\s*ai",
    r"นักปราชญ์",
    r"โดราเอมอน",
    r"ปรัชญา",
    r"มาเคียเวลลี",
)

SECURITY_DANGER_PATTERNS: tuple[str, ...] = (
    r"bypass.*security",
    r"security\s+system",
    r"hack",
    r"แฮก",
    r"รหัสผ่าน",
    r"ร\s*ห\s*ั?\s*ส\s*ผ\s*่?\s*า\s*น",
    r"password",
    r"credential",
    r"เลี่ยงระบบ",
    r"เจาะระบบ",
    r"wifi",
    r"wi-fi",
)

SECURITY_DANGER_COMPACT_PATTERNS: tuple[str, ...] = (
    r"รหัสผ่าน",
    r"รหสผาน",
    r"แฮก",
    r"แฮกรหัส",
    r"แฮกwifi",
    r"hackwifi",
    r"password",
    r"bypasssecurity",
    r"securitysystem",
)

HARMFUL_DANGER_PATTERNS: tuple[str, ...] = (
    r"ระเบิด",
    r"ระเบิดควัน",
    r"ผลิตระเบิด",
    r"ทำระเบิด",
    r"วิธีทำ.*(?:ระเบิด|อาวุธ)",
    r"อาวุธ",
    r"วางยา",
)

EMERGENCY_PATTERNS: tuple[str, ...] = (
    r"งูกัด",
    r"โดนงูกัด",
    r"ฉุกเฉิน",
    r"ด่วนมาก",
    r"เลือดออก",
    r"หมดสติ",
)

FOLLOWUP_MARKERS: tuple[str, ...] = (
    "งั้น",
    "ถ้างั้น",
    "แล้ว",
    "บ้างไหม",
    "บ้างมั้ย",
    "อีก",
    "แบบนั้น",
    "แบบนี้",
    "นี้",
    "นั้น",
    "ล่าสุด",
)

GENERIC_QUERY_PHRASES: tuple[str, ...] = (
    "น้องหลงทาง",
    "ช่วย",
    "ของ",
    "แนะนำ",
    "ตามหา",
    "ค้นดู",
    "ค้น",
    "หา",
    "สินค้า",
    "สินค้าชิ้นไหน",
    "ชิ้นไหน",
    "ตัวไหน",
    "อันไหน",
    "รายการไหน",
    "ชื่อว่า",
    "อยู่ไหน",
    "มีไหม",
    "มีมั้ย",
    "มีกี่",
    "มี",
    "ไหม",
    "มั้ย",
    "ไหน",
    "อะไร",
    "บ้าง",
    "อะไรบ้าง",
    "มีอะไรบ้าง",
    "ขาย",
    "ขายบ้าง",
    "อะไรขายบ้าง",
    "มีอะไรขายบ้าง",
    "หน่อย",
    "หน่อยสิ",
    "กับ",
    "และ",
    "อยู่",
    "อยู่ตรง",
    "อยู่ตรงไหน",
    "ไม่เจอ",
    "ตรง",
    "ตรงไหน",
    "id",
    "รหัส",
    "รหัสสินค้า",
    "เลข",
    "หมายเลข",
    "น่าสนใจ",
    "อะไรที่",
    "เป็น",
    "ที่เป็น",
    "ประเภท",
    "หมวด",
    "มา",
    "ให้",
    "ครับ",
    "ค่ะ",
    "คะ",
    "นะ",
    "สิ",
    "ที่",
    "ที่มี",
    "ใน",
    "ราคา",
    "งบ",
    "บาท",
    "ไม่เกิน",
    "ต่ำกว่า",
    "ต่ำกว่าสิบ",
    "น้อยกว่า",
    "น้อยกว่าสิบ",
    "มากกว่า",
    "ตั้งแต่",
    "อย่างน้อย",
    "สัก",
    "แค่",
    "รายการ",
    "อย่าง",
    "ชิ้น",
    "ตัว",
    "อัน",
    "ถุง",
    "หน่วย",
    "แบรนด์",
    "แบรนด์นี้",
    "ยี่ห้อ",
    "ยี่ห้อนี้",
    "พวกนี้",
    "รายการนี้",
    "ตัวนี้",
    "ชิ้นนี้",
    "อันนี้",
    "ล่าสุด",
    "สต็อก",
    "สต๊อก",
    "stock",
    "คงเหลือ",
    "เหลือ",
    "ศูนย์",
    "สิบ",
    "เก้า",
    "แปด",
    "เจ็ด",
    "หก",
    "ห้า",
    "สี่",
    "สาม",
    "สอง",
    "หนึ่ง",
    "หมด",
    "หมดแล้ว",
)

BROAD_CATEGORY_WORDS: tuple[str, ...] = (
    "อาหาร",
    "ของกิน",
    "ของใช้ทั่วไป",
    "ของใช้",
    "เสื้อผ้า",
    "เครื่องใช้ไฟฟ้า",
    "ยาสามัญ",
    "ไฟฟ้า",
)

OUT_OF_STOCK_PATTERNS: tuple[str, ...] = (
    r"(?:สต็อก|สต๊อก|stock)\s*(?:=|เท่ากับ)?\s*0",
    r"(?:คงเหลือ|เหลือ)\s*(?:=|เท่ากับ)?\s*(?:0|ศูนย์)",
    r"(?:สต็อก|สต๊อก|stock)\s*(?:หมด|ศูนย์)",
    r"(?:หมด\s*(?:สต็อก|สต๊อก)|ของหมด)",
    r"หมดแล้ว",
)

IN_STOCK_PATTERNS: tuple[str, ...] = (
    r"มีของ",
    r"มี\s*(?:สต็อก|สต๊อก|stock)",
    r"พร้อมขาย",
    r"ยังไม่หมด",
    r"ไม่หมด",
)

STOCK_QUERY_PATTERNS: tuple[str, ...] = (
    r"(?:สต็อก|สต๊อก|stock|คงเหลือ)",
    r"เหลือ\s*(?:กี่|เท่าไหร่|เท่าไร|จำนวน)",
    r"มีกี่\s*(?:ชิ้น|ถุง|อัน|ตัว|เครื่อง|หน่วย)?",
    r"กี่\s*(?:ชิ้น|ถุง|อัน|ตัว|เครื่อง|หน่วย)",
    r"หมดแล้ว",
    r"เหลือ\s*(?:0|ศูนย์)",
)

STOCK_REFERENCE_PATTERNS: tuple[str, ...] = (
    r"แบรนด์นี้",
    r"ยี่ห้อนี้",
    r"รายการนี้",
    r"ตัวนี้",
    r"ชิ้นนี้",
    r"อันนี้",
    r"พวกนี้",
    r"จากผลล่าสุด",
    r"ล่าสุด",
)

BROAD_CATEGORY_PATTERNS: tuple[str, ...] = (
    r"มี\s*อะไร\s*บ้าง",
    r"อะไร\s*บ้าง",
    r"อะไร\s*ขาย\s*บ้าง",
    r"ขาย\s*อะไร\s*บ้าง",
    r"มี\s*.*อะไร\s*ขาย\s*บ้าง",
    r"มี\s*สินค้า\s*อะไร",
    r"มี\s*ของ\s*อะไร",
    r"ใน\s*หมวด",
    r"ที่\s*เป็น",
    r"แนะนำ",
    r"ดู\s*(?:สินค้า|ของ)?",
)

THAI_STOCK_NUMBER_WORDS: dict[str, int] = {
    **THAI_NUMBER_WORDS,
    "ศูนย์": 0,
}


class DeepSeekReasoningClient:
    def __init__(self) -> None:
        api_key = os.getenv("DEEPSEEK_API_KEY")
        if not api_key:
            raise RuntimeError("DEEPSEEK_API_KEY is not set.")

        self.model = os.getenv("DEEPSEEK_MODEL", "deepseek-v4-pro")
        self.reasoning_effort = os.getenv("DEEPSEEK_REASONING_EFFORT", "high")
        self.max_tokens = int(os.getenv("DEEPSEEK_MAX_TOKENS", "2048"))
        self.client = AsyncOpenAI(
            api_key=api_key,
            base_url=os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com"),
        )

    async def acomplete(
        self,
        messages: list[dict[str, str]],
        callbacks: Optional[Iterable[Any]] = None,
        *,
        max_tokens: Optional[int] = None,
    ) -> tuple[str, str]:
        request: dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "stream": True,
            "max_tokens": max_tokens or self.max_tokens,
            "reasoning_effort": self.reasoning_effort,
            "extra_body": {"thinking": {"type": "enabled"}},
        }

        content_parts: list[str] = []
        reasoning_parts: list[str] = []
        stream = await self.client.chat.completions.create(**request)

        async for chunk in stream:
            if not chunk.choices:
                continue
            delta = chunk.choices[0].delta
            reasoning_delta = _extract_delta_value(delta, "reasoning_content") or _extract_delta_value(delta, "thought")
            content_delta = _extract_delta_value(delta, "content")

            if reasoning_delta:
                reasoning_parts.append(reasoning_delta)
                await _notify_reasoning_delta(callbacks, reasoning_delta)
            if content_delta:
                content_parts.append(content_delta)

        reasoning = "".join(reasoning_parts)
        await _notify_reasoning_complete(callbacks, reasoning)
        return "".join(content_parts).strip(), reasoning


def _extract_delta_value(delta: Any, key: str) -> str:
    value = getattr(delta, key, None)
    if value:
        return str(value)
    if hasattr(delta, "model_dump"):
        dumped = delta.model_dump(exclude_none=True)
        value = dumped.get(key)
        if value:
            return str(value)
    if isinstance(delta, dict):
        value = delta.get(key)
        if value:
            return str(value)
    return ""


async def _maybe_await(value: Any) -> None:
    if inspect.isawaitable(value):
        await value


async def _notify_reasoning_delta(callbacks: Optional[Iterable[Any]], token: str) -> None:
    for callback in callbacks or []:
        handler = getattr(callback, "on_reasoning_delta", None)
        if handler:
            await _maybe_await(handler(token))


async def _notify_reasoning_complete(callbacks: Optional[Iterable[Any]], reasoning: str) -> None:
    for callback in callbacks or []:
        handler = getattr(callback, "on_reasoning_complete", None)
        if handler:
            await _maybe_await(handler(reasoning))


def _callbacks_from_config(config: Optional[RunnableConfig]) -> list[Any]:
    if not config:
        return []
    callbacks = config.get("callbacks") if isinstance(config, dict) else None
    if callbacks is None:
        return []
    if isinstance(callbacks, list):
        return callbacks
    handlers = getattr(callbacks, "handlers", None)
    if handlers is not None:
        return list(handlers)
    return [callbacks]


@lru_cache(maxsize=1)
def get_deepseek_client() -> DeepSeekReasoningClient:
    return DeepSeekReasoningClient()


@lru_cache(maxsize=1)
def get_embedding_model() -> SentenceTransformer:
    model_name = os.getenv("EMBEDDING_MODEL", "intfloat/multilingual-e5-large")
    return SentenceTransformer(model_name)


@lru_cache(maxsize=1)
def get_supabase_client() -> Any:
    from supabase import create_client

    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_ANON_KEY")
    if not url or not key:
        raise RuntimeError("Set SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY or SUPABASE_ANON_KEY.")
    return create_client(url, key)


def table_name() -> str:
    return os.getenv("PRODUCT_TABLE", "products")


def latest_user_text(state: MallState) -> str:
    for message in reversed(state.get("messages", [])):
        if isinstance(message, HumanMessage):
            return _content_to_text(message.content)
        if isinstance(message, dict) and message.get("role") in {"user", "human"}:
            return _content_to_text(message.get("content", ""))
    return ""


def normalize_user_text(text: str) -> str:
    normalized = unicodedata.normalize("NFC", text)
    return normalized.replace("\u0e4d\u0e32", "\u0e33")


def _content_to_text(content: Any) -> str:
    if isinstance(content, str):
        return normalize_user_text(content)
    if isinstance(content, list):
        joined = " ".join(str(part.get("text", part)) if isinstance(part, dict) else str(part) for part in content)
        return normalize_user_text(joined)
    return normalize_user_text(str(content))


def _json_from_text(text: str) -> dict[str, Any]:
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", text, flags=re.DOTALL)
        if not match:
            return {}
        try:
            return json.loads(match.group(0))
        except json.JSONDecodeError:
            return {}


def compact_text(text: str) -> str:
    text = normalize_user_text(text)
    return re.sub(r"[\s\W_]+", "", text.lower(), flags=re.UNICODE)


def _matches_any_pattern(text: str, patterns: Iterable[str]) -> bool:
    text = normalize_user_text(text)
    return any(re.search(pattern, text, flags=re.IGNORECASE) for pattern in patterns)


def _matches_any_compact_pattern(text: str, patterns: Iterable[str]) -> bool:
    compact = compact_text(text)
    return any(re.search(pattern, compact, flags=re.IGNORECASE) for pattern in patterns)


def detects_prompt_injection(text: str) -> bool:
    return _matches_any_pattern(text, PROMPT_INJECTION_PATTERNS) or _matches_any_compact_pattern(
        text, PROMPT_INJECTION_COMPACT_PATTERNS
    )


def detects_security_danger(text: str) -> bool:
    return _matches_any_pattern(text, SECURITY_DANGER_PATTERNS) or _matches_any_compact_pattern(
        text, SECURITY_DANGER_COMPACT_PATTERNS
    )


def detects_harmful_danger(text: str) -> bool:
    return _matches_any_pattern(text, HARMFUL_DANGER_PATTERNS)


def detects_emergency(text: str) -> bool:
    return _matches_any_pattern(text, EMERGENCY_PATTERNS)


def detects_out_of_stock_query(text: str) -> bool:
    return _matches_any_pattern(text, OUT_OF_STOCK_PATTERNS)


def detects_in_stock_query(text: str) -> bool:
    return _matches_any_pattern(text, IN_STOCK_PATTERNS)


def detects_stock_query(text: str) -> bool:
    return _matches_any_pattern(text, STOCK_QUERY_PATTERNS) or detects_out_of_stock_query(text)


def detects_stock_reference(text: str) -> bool:
    return _matches_any_pattern(text, STOCK_REFERENCE_PATTERNS)


def detects_broad_category_query(text: str) -> bool:
    return _matches_any_pattern(text, BROAD_CATEGORY_PATTERNS)


def detects_specific_product_type_query(text: str) -> bool:
    normalized = normalize_user_text(text)
    return any(keyword in normalized for keyword in SPECIFIC_PRODUCT_TYPE_KEYWORDS)


def detects_out_of_domain(text: str) -> bool:
    return (
        _matches_any_pattern(text, CODING_OUT_OF_DOMAIN_PATTERNS)
        or _matches_any_pattern(text, FINANCE_OUT_OF_DOMAIN_PATTERNS)
        or _matches_any_pattern(text, OUTSIDE_MALL_PATTERNS)
        or _matches_any_pattern(text, ROLEPLAY_OUT_OF_DOMAIN_PATTERNS)
    )


def detects_unsupported_route_request(text: str) -> bool:
    if not wants_summary(text):
        return False
    return bool(re.search(r"(?:ชั้น\s*\d+|ดาดฟ้า|roof|rooftop|floor\s*\d+)", text, flags=re.IGNORECASE))


def detects_model_meta_question(text: str) -> bool:
    lowered = text.lower()
    meta_terms = ("โมเดล", "model", "บริษัท", "เบื้องหลัง", "llm", "deepseek")
    return "น้องหลงทาง" in text and any(term in lowered for term in meta_terms)


def model_meta_response() -> str:
    model = os.getenv("DEEPSEEK_MODEL", "deepseek-v4-pro")
    embedding_model = os.getenv("EMBEDDING_MODEL", "intfloat/multilingual-e5-large")
    return (
        f"{CATCHPHRASE} น้องหลงทางเป็นผู้ช่วยหาสินค้าในโปรเจกต์ AIหน้าฮ่านครับ "
        f"ฝั่งภาษาใช้โมเดลที่ตั้งไว้ใน `.env` คือ `{model}` และฝั่งค้นหาสินค้าใช้ embedding `{embedding_model}` "
        "น้องไม่เปิดเผย API key หรือคำสั่งระบบภายในนะครับ"
    )


def deterministic_direct_response(text: str) -> Optional[str]:
    if detects_emergency(text):
        return EMERGENCY_TEXT
    if detects_harmful_danger(text):
        return HARMFUL_REFUSAL_TEXT
    if detects_security_danger(text):
        return SECURITY_REFUSAL_TEXT
    if detects_prompt_injection(text):
        return PROMPT_INJECTION_TEXT
    if detects_unsupported_route_request(text):
        return UNSUPPORTED_ROUTE_TEXT
    if detects_out_of_domain(text):
        return OUT_OF_SCOPE_TEXT
    if detects_model_meta_question(text):
        return model_meta_response()
    return None


def is_greeting(text: str) -> bool:
    cleaned = re.sub(r"\s+", "", text.strip().lower())
    return cleaned in {"hi", "hello", "hey", "สวัสดี", "หวัดดี", "ดีครับ", "ดีค่ะ"}


def is_capability_question(text: str) -> bool:
    lowered = text.lower()
    return any(
        keyword in lowered
        for keyword in (
            "ทำอะไรได้",
            "ช่วยอะไรได้",
            "ใช้งานยังไง",
            "หาอะไรได้",
            "หมวดอะไร",
            "categories",
            "help",
        )
    )


def is_ambiguous_recommendation(text: str) -> bool:
    if "แนะนำ" not in text and "recommend" not in text.lower():
        return False
    if infer_category(text) or extract_quoted_terms(text) or extract_explicit_brand(text):
        return False
    terms = product_query_terms(text, {})
    return not terms or "อะไรก็ได้" in text


def is_short_product_name_query(text: str) -> bool:
    stripped = strip_query_affixes(text)
    if not stripped or len(stripped) > 40:
        return False
    if re.search(r"(?:คิด|ทำไม|ยังไง|อย่างไร|ก่อน|หรอ|เหรอ|หรือ|ใคร|เมื่อไหร่)", stripped):
        return False
    return bool(product_query_terms(stripped, {}))


def dedupe_ints(values: Iterable[int]) -> list[int]:
    result: list[int] = []
    for value in values:
        int_value = int(value)
        if int_value not in result:
            result.append(int_value)
    return result


def parse_product_ids_for_lookup(text: str) -> list[int]:
    if has_add_request(text):
        return []

    explicit_values = [
        int(match.group(1))
        for match in re.finditer(r"(?:id|ID|รหัส(?:สินค้า)?|หมายเลข|เลข)\s*#?\s*(\d+)", text, flags=re.IGNORECASE)
    ]
    cleaned = normalize_user_text(text).lower()
    cleaned = re.sub(
        r"(?:id|รหัส(?:สินค้า)?|สินค้า|รายการ|หมายเลข|เลข|หา|ค้น|ดู|อยู่ไหน|อยู่ตรงไหน|ตรงไหน|อยู่|ตรง|และ|กับ|,|，|#)",
        " ",
        cleaned,
        flags=re.IGNORECASE,
    )
    cleaned = re.sub(r"[\d\s]+", " ", cleaned)
    if cleaned.strip():
        return dedupe_ints(explicit_values)

    bare_values = [int(match.group(0)) for match in re.finditer(r"\d+", text)]
    return dedupe_ints([*explicit_values, *bare_values])


def deterministic_general_response(text: str) -> str:
    if is_greeting(text):
        return f"{CATCHPHRASE} สวัสดีครับ น้องหลงทางพร้อมช่วยหาสินค้าในห้างแล้วครับ"
    if is_capability_question(text) or is_ambiguous_recommendation(text):
        return CLARIFY_CATEGORY_TEXT
    return OUT_OF_SCOPE_TEXT


def heuristic_route(text: str) -> str:
    lowered = text.lower()
    summary_keywords = (
        "สรุป",
        "checkout",
        "เช็คเอาท์",
        "คิดเงิน",
        "ตะกร้า",
        "ลิสต์",
        "เส้นทาง",
    )
    search_keywords = (
        "หา",
        "อยู่ไหน",
        "มีไหม",
        "มีมั้ย",
        "มีกี่",
        "เหลือ",
        "คงเหลือ",
        "สต็อก",
        "สต๊อก",
        "stock",
        "ราคา",
        "ไม่เกิน",
        "ต่ำกว่า",
        "มากกว่า",
        "ซื้อ",
        "อยากได้",
        "แนะนำ",
        "ค้น",
        "ค้นดู",
    )
    if any(keyword in lowered for keyword in summary_keywords):
        return "cart"
    if has_add_request(text):
        return "cart"
    if is_greeting(text) or is_capability_question(text) or is_ambiguous_recommendation(text):
        return "general"
    if detects_stock_query(text):
        return "search"
    if parse_product_ids_for_lookup(text):
        return "search"
    if any(keyword in lowered for keyword in search_keywords) or infer_category(text):
        return "search"
    if is_short_product_name_query(text):
        return "search"
    return "general"


async def supervisor_node(state: MallState, config: Optional[RunnableConfig] = None) -> MallState:
    del config
    user_text = latest_user_text(state)
    direct_response = deterministic_direct_response(user_text)
    if direct_response:
        return {
            "route": "direct",
            "direct_response": direct_response,
            "current_context": "deterministic_guard",
            "shopping_list": state.get("shopping_list", []),
            "constraints": {},
            "search_results": [],
            "validated_results": [],
        }

    route = heuristic_route(user_text)
    reason = f"deterministic:{route}"

    return {
        "route": route,
        "current_context": reason,
        "shopping_list": state.get("shopping_list", []),
    }


def route_after_supervisor(state: MallState) -> str:
    return state.get("route", "general")


def infer_category(text: str) -> Optional[str]:
    if not text:
        return None
    for category in ALLOWED_CATEGORIES:
        if category in text:
            return category
    for keyword, category in sorted(THAI_CATEGORY_KEYWORDS.items(), key=lambda item: len(item[0]), reverse=True):
        if keyword in text:
            return category
    return None


STOCK_NUMBER_PATTERN = r"\d+|ศูนย์|หนึ่ง|สอง|สาม|สี่|ห้า|หก|เจ็ด|แปด|เก้า|สิบ"


def parse_stock_number(raw_value: str) -> Optional[int]:
    value = normalize_user_text(raw_value).strip()
    if value.isdigit():
        return int(value)
    return THAI_STOCK_NUMBER_WORDS.get(value)


def infer_stock_constraints(text: str) -> SearchConstraints:
    normalized = normalize_user_text(text).replace(",", "")
    constraints: SearchConstraints = {}

    upper_patterns = (
        rf"(?:สต็อก|สต๊อก|stock|คงเหลือ|เหลือ)[^\dก-๙]{{0,12}}(?:ต่ำกว่า|น้อยกว่า|<)\s*({STOCK_NUMBER_PATTERN})",
        rf"(?:ต่ำกว่า|น้อยกว่า|<)\s*({STOCK_NUMBER_PATTERN})\s*(?:ชิ้น|ถุง|อัน|ตัว|เครื่อง|หน่วย)",
    )
    inclusive_upper_patterns = (
        rf"(?:สต็อก|สต๊อก|stock|คงเหลือ|เหลือ)[^\dก-๙]{{0,12}}(?:ไม่เกิน|ไม่เกินกว่า|<=)\s*({STOCK_NUMBER_PATTERN})",
        rf"(?:ไม่เกิน|ไม่เกินกว่า|<=)\s*({STOCK_NUMBER_PATTERN})\s*(?:ชิ้น|ถุง|อัน|ตัว|เครื่อง|หน่วย)",
    )
    lower_patterns = (
        rf"(?:สต็อก|สต๊อก|stock|คงเหลือ|เหลือ)[^\dก-๙]{{0,12}}(?:มากกว่า|เกินกว่า|>)\s*({STOCK_NUMBER_PATTERN})",
        rf"(?:มากกว่า|เกินกว่า|>)\s*({STOCK_NUMBER_PATTERN})\s*(?:ชิ้น|ถุง|อัน|ตัว|เครื่อง|หน่วย)",
    )
    inclusive_lower_patterns = (
        rf"(?:สต็อก|สต๊อก|stock|คงเหลือ|เหลือ)[^\dก-๙]{{0,12}}(?:ตั้งแต่|อย่างน้อย|>=)\s*({STOCK_NUMBER_PATTERN})",
        rf"(?:ตั้งแต่|อย่างน้อย|>=)\s*({STOCK_NUMBER_PATTERN})\s*(?:ชิ้น|ถุง|อัน|ตัว|เครื่อง|หน่วย)",
    )

    for pattern in upper_patterns:
        match = re.search(pattern, normalized)
        if match:
            value = parse_stock_number(match.group(1))
            if value is not None:
                constraints["max_stock"] = max(0, value - 1)
                break

    if "max_stock" not in constraints:
        for pattern in inclusive_upper_patterns:
            match = re.search(pattern, normalized)
            if match:
                value = parse_stock_number(match.group(1))
                if value is not None:
                    constraints["max_stock"] = max(0, value)
                    break

    for pattern in lower_patterns:
        match = re.search(pattern, normalized)
        if match:
            value = parse_stock_number(match.group(1))
            if value is not None:
                constraints["min_stock"] = value + 1
                break

    if "min_stock" not in constraints:
        for pattern in inclusive_lower_patterns:
            match = re.search(pattern, normalized)
            if match:
                value = parse_stock_number(match.group(1))
                if value is not None:
                    constraints["min_stock"] = value
                    break

    return constraints


def price_filter_text(text: str) -> str:
    normalized = normalize_user_text(text).replace(",", "")
    stock_expression_patterns = (
        rf"(?:สต็อก|สต๊อก|stock|คงเหลือ|เหลือ)\s*(?:ต่ำกว่า|น้อยกว่า|มากกว่า|เกินกว่า|ไม่เกิน|ไม่เกินกว่า|ตั้งแต่|อย่างน้อย|<=|>=|<|>)\s*(?:{STOCK_NUMBER_PATTERN})",
        rf"(?:ต่ำกว่า|น้อยกว่า|มากกว่า|เกินกว่า|ไม่เกิน|ไม่เกินกว่า|ตั้งแต่|อย่างน้อย|<=|>=|<|>)\s*(?:{STOCK_NUMBER_PATTERN})\s*(?:ชิ้น|ถุง|อัน|ตัว|เครื่อง|หน่วย)",
        rf"(?:สต็อก|สต๊อก|stock|คงเหลือ|เหลือ)\s*(?:=|เท่ากับ)?\s*(?:{STOCK_NUMBER_PATTERN})",
    )
    for pattern in stock_expression_patterns:
        normalized = re.sub(pattern, " ", normalized, flags=re.IGNORECASE)
    return normalized


def query_terms_filter_text(text: str) -> str:
    normalized = price_filter_text(text)
    price_expression_patterns = (
        r"(?:งบ|ราคา)?\s*(?:ไม่\s*เกิน|ต่ำกว่า|น้อยกว่า|มากกว่า|เกินกว่า|ตั้งแต่|อย่างน้อย|<=|>=|<|>)\s*\d+(?:\.\d+)?\s*(?:บาท)?",
        r"(?:งบ|ราคา)\s*\d+(?:\.\d+)?\s*(?:บาท)?",
        r"\d+(?:\.\d+)?\s*บาท",
    )
    for pattern in price_expression_patterns:
        normalized = re.sub(pattern, " ", normalized, flags=re.IGNORECASE)
    return normalized


def deterministic_constraints(text: str) -> SearchConstraints:
    constraints: SearchConstraints = {"in_stock_only": False}
    category = infer_category(text)
    if category:
        constraints["category"] = category
        if detects_broad_category_query(text) and not detects_specific_product_type_query(text):
            constraints["broad_category_query"] = True
    if detects_stock_query(text):
        constraints["stock_query"] = True

    normalized = price_filter_text(text)
    range_match = re.search(r"(?:ระหว่าง|ตั้งแต่)\s*(\d+(?:\.\d+)?)\s*(?:-|ถึง|จนถึง)\s*(\d+(?:\.\d+)?)", normalized)
    if range_match:
        low, high = sorted((float(range_match.group(1)), float(range_match.group(2))))
        constraints["min_price"] = low
        constraints["max_price"] = high

    max_match = re.search(r"(?:ไม่\s*เกิน|ต่ำกว่า|น้อยกว่า|<=|<)\s*(\d+(?:\.\d+)?)", normalized)
    if max_match:
        constraints["max_price"] = float(max_match.group(1))

    min_match = re.search(
        r"(?:มากกว่า|เกินกว่า|ตั้งแต่|ขั้นต่ำ|อย่างน้อย|>=|>)\s*(\d+(?:\.\d+)?)",
        normalized,
    )
    if not min_match and not re.search(r"ไม่\s*เกิน\s*\d", normalized):
        min_match = re.search(r"เกิน\s*(\d+(?:\.\d+)?)", normalized)
    if min_match:
        constraints["min_price"] = float(min_match.group(1))

    if detects_out_of_stock_query(text):
        constraints["stock_status"] = "out_of_stock"
        constraints["in_stock_only"] = False
    elif detects_in_stock_query(text):
        constraints["stock_status"] = "in_stock"
        constraints["in_stock_only"] = True

    stock_constraints = infer_stock_constraints(text)
    constraints.update(stock_constraints)
    if constraints.get("max_stock") is not None and "stock_status" not in constraints:
        constraints["in_stock_only"] = True

    result_shape = infer_result_shape(text)
    constraints.update(result_shape)
    if detects_brand_listing_query(text) and not constraints.get("stock_query"):
        constraints["group_by"] = "brand"
    if result_shape.get("max_results") and "ขนม" in normalize_user_text(text):
        constraints["diversify_results"] = True
    return constraints


def parse_count_token(token: str) -> Optional[int]:
    token = token.strip()
    if token.isdigit():
        return int(token)
    return THAI_NUMBER_WORDS.get(token)


def infer_result_shape(text: str) -> SearchConstraints:
    count_token = r"\d+|หนึ่ง|สอง|สาม|สี่|ห้า|หก|เจ็ด|แปด|เก้า|สิบ"
    brand_patterns = (
        rf"({count_token})\s*(?:แบรนด์|ยี่ห้อ)",
        rf"(?:แบรนด์|ยี่ห้อ)\s*(?:มา|ให้|สัก|แค่)?\s*({count_token})",
    )
    for pattern in brand_patterns:
        match = re.search(pattern, text)
        if match:
            count = parse_count_token(match.group(1))
            if count:
                return {"max_results": max(1, min(count, 20)), "group_by": "brand"}

    product_patterns = (
        rf"({count_token})\s*(?:รายการ|ชิ้น|ตัว|อัน|อย่าง)",
        rf"(?:รายการ|สินค้า)\s*(?:มา|ให้|สัก|แค่)?\s*({count_token})",
    )
    for pattern in product_patterns:
        match = re.search(pattern, text)
        if match:
            count = parse_count_token(match.group(1))
            if count:
                return {"max_results": max(1, min(count, 20)), "group_by": "product"}

    return {}


async def llm_constraints(text: str, callbacks: list[Any]) -> SearchConstraints:
    system = (
        f"{SUPERVISOR_GUARDRAIL_PROMPT}\n"
        "Extract only explicit filters from the user text. "
        f"Allowed categories: {', '.join(ALLOWED_CATEGORIES)}. "
        "Return strict JSON only: {\"category\": null|string, \"min_price\": null|number, "
        "\"max_price\": null|number, \"in_stock_only\": boolean}. "
        "Do not infer a product name and do not invent products."
    )
    messages = [{"role": "system", "content": system}, {"role": "user", "content": text}]
    content, _ = await get_deepseek_client().acomplete(messages, callbacks, max_tokens=512)
    payload = _json_from_text(content)
    constraints: SearchConstraints = {"in_stock_only": bool(payload.get("in_stock_only", False))}

    category = payload.get("category")
    if isinstance(category, str) and category.strip():
        try:
            constraints["category"] = normalize_category(category.strip())
        except ValueError:
            pass

    for source_key in ("min_price", "max_price"):
        value = payload.get(source_key)
        if value is not None:
            try:
                constraints[source_key] = float(value)
            except (TypeError, ValueError):
                pass
    return constraints


def merge_constraints(primary: SearchConstraints, secondary: SearchConstraints) -> SearchConstraints:
    stock_status = primary.get("stock_status") or secondary.get("stock_status")
    merged: SearchConstraints = {
        "in_stock_only": bool(primary.get("in_stock_only") or secondary.get("in_stock_only")),
        "stock_query": bool(primary.get("stock_query") or secondary.get("stock_query")),
        "broad_category_query": bool(primary.get("broad_category_query") or secondary.get("broad_category_query")),
        "diversify_results": bool(primary.get("diversify_results") or secondary.get("diversify_results")),
    }
    if stock_status:
        merged["stock_status"] = stock_status
        merged["in_stock_only"] = stock_status == "in_stock"

    for key in ("category", "min_price", "max_price", "min_stock", "max_stock", "max_results", "group_by"):
        value = primary.get(key)
        if value is None:
            value = secondary.get(key)
        if value is not None:
            merged[key] = value  # type: ignore[literal-required]
    return merged


def has_explicit_price_filter(text: str) -> bool:
    normalized = price_filter_text(text)
    return bool(
        re.search(
            r"(?:ไม่\s*เกิน|ต่ำกว่า|น้อยกว่า|มากกว่า|เกินกว่า|(?<!ไม่)เกิน|ตั้งแต่|ระหว่าง|ขั้นต่ำ|อย่างน้อย|<=|>=|<|>)\s*\d",
            normalized,
        )
    )


def has_explicit_max_price_filter(text: str) -> bool:
    normalized = price_filter_text(text)
    return bool(re.search(r"(?:ไม่\s*เกิน|ต่ำกว่า|น้อยกว่า|<=|<)\s*\d", normalized))


def has_explicit_min_price_filter(text: str) -> bool:
    normalized = price_filter_text(text)
    if re.search(r"(?:มากกว่า|เกินกว่า|ตั้งแต่|ระหว่าง|ขั้นต่ำ|อย่างน้อย|>=|>)\s*\d", normalized):
        return True
    return bool(re.search(r"เกิน\s*\d", normalized) and not re.search(r"ไม่\s*เกิน\s*\d", normalized))


def sanitize_constraints_for_text(constraints: SearchConstraints, text: str) -> SearchConstraints:
    sanitized: SearchConstraints = dict(constraints)  # type: ignore[assignment]
    if has_explicit_max_price_filter(text) and not has_explicit_min_price_filter(text):
        sanitized.pop("min_price", None)
    return sanitized


def looks_like_followup(text: str) -> bool:
    return any(marker in text for marker in FOLLOWUP_MARKERS)


def inherit_followup_constraints(
    current: SearchConstraints,
    previous: Optional[SearchConstraints],
    text: str,
) -> SearchConstraints:
    if not previous or not looks_like_followup(text):
        return current

    inherited: SearchConstraints = dict(current)  # type: ignore[assignment]
    if "category" not in inherited and previous.get("category"):
        inherited["category"] = previous["category"]

    if detects_broad_category_query(text) and inherited.get("category") and not detects_specific_product_type_query(text):
        inherited["broad_category_query"] = True

    if not has_explicit_price_filter(text):
        for key in ("min_price", "max_price"):
            if key not in inherited and previous.get(key) is not None:
                inherited[key] = previous[key]  # type: ignore[literal-required]

    if detects_stock_query(text):
        inherited["stock_query"] = True

    if not detects_stock_query(text):
        for key in ("min_stock", "max_stock"):
            if key not in inherited and previous.get(key) is not None:
                inherited[key] = previous[key]  # type: ignore[literal-required]

    if not inherited.get("in_stock_only") and previous.get("in_stock_only"):
        inherited["in_stock_only"] = True

    if "stock_status" not in inherited and previous.get("stock_status"):
        inherited["stock_status"] = previous["stock_status"]
        inherited["in_stock_only"] = previous["stock_status"] == "in_stock"

    return inherited


def embed_query(query: str) -> list[float]:
    model = get_embedding_model()
    vector = model.encode([f"query: {query}"], normalize_embeddings=True)[0]
    return [float(value) for value in vector]


def normalize_product(raw: dict[str, Any]) -> Product:
    product: Product = {
        "id": int(raw["id"]),
        "name": str(raw.get("name") or ""),
        "brand": str(raw.get("brand") or ""),
        "category": str(raw.get("category") or ""),
        "description": str(raw.get("description") or ""),
        "price": float(raw.get("price") or 0.0),
        "stock_quantity": int(raw.get("stock_quantity") or 0),
        "location_info": parse_location_info(raw.get("location_info", {})),
        "coordinates_3d": parse_location_info(raw.get("coordinates_3d", {})),
    }
    if "similarity" in raw and raw["similarity"] is not None:
        product["similarity"] = float(raw["similarity"])
    return product


def keyword_for_search(text: str, constraints: Optional[SearchConstraints] = None) -> str:
    return " ".join(product_query_terms(text, constraints or {})[:6])


def normalize_match_text(text: str) -> str:
    return re.sub(r"[^0-9a-zA-Zก-๙]+", "", normalize_user_text(text).lower(), flags=re.UNICODE)


def significant_tokens(text: str) -> list[str]:
    cleaned = re.sub(r"[^\wก-๙\s]", " ", text.lower(), flags=re.UNICODE)
    stopwords = {
        "หา",
        "ตามหา",
        "อยากได้",
        "สินค้า",
        "ราคา",
        "มี",
        "ไหม",
        "มั้ย",
        "ครับ",
        "ค่ะ",
        "คะ",
        "รุ่น",
        "สี",
        "ขนาด",
        "ยี่ห้อ",
        "แบรนด์",
    }
    return [token for token in cleaned.split() if token not in stopwords and not token.isdigit()]


def extract_quoted_terms(text: str) -> list[str]:
    terms = [
        match.strip()
        for match in re.findall(r"['\"“”‘’]([^'\"“”‘’]{2,80})['\"“”‘’]", text)
        if match.strip()
    ]
    return [term for term in terms if not term.startswith("[") and not term.endswith("]")]


def extract_explicit_brand(text: str) -> Optional[str]:
    if re.search(r"(?:ยี่ห้อ|แบรนด์)\s*(?:นี้|นั้น|ล่าสุด|พวกนี้)", text, flags=re.IGNORECASE):
        return None

    match = re.search(r"(?:ยี่ห้อ|แบรนด์)\s*([^\n,，.!?]+)", text, flags=re.IGNORECASE)
    if not match:
        return None
    raw = match.group(1).strip(" '\"“”‘’")
    raw = re.split(r"['\"“”‘’]", raw, maxsplit=1)[0]
    raw = re.split(r"\s+(?:ราคา|มี|อยู่|ขาย|กี่|ไหม|มั้ย|งบ|ไม่เกิน|ต่ำกว่า|มากกว่า)\b", raw, maxsplit=1)[0]
    tokens = raw.split()
    if not tokens:
        return None
    candidate = " ".join(tokens[:3]).strip()
    generic_values = (
        {item.lower() for item in GENERIC_QUERY_PHRASES}
        | {item.lower() for item in BROAD_CATEGORY_WORDS}
        | set(THAI_NUMBER_WORDS)
        | {item.lower() for item in ALLOWED_CATEGORIES}
    )
    first_token = tokens[0].strip().lower()
    if (
        candidate.lower() in generic_values
        or first_token in generic_values
        or infer_category(raw) is not None
        or candidate.isdigit()
    ):
        return None
    return candidate


def detects_brand_listing_query(text: str) -> bool:
    if not re.search(r"(?:ยี่ห้อ|แบรนด์)", text, flags=re.IGNORECASE):
        return False
    if re.search(r"(?:ยี่ห้อ|แบรนด์)\s*(?:นี้|นั้น|ล่าสุด|พวกนี้)", text, flags=re.IGNORECASE):
        return False
    return extract_explicit_brand(text) is None and bool(infer_category(text) or detects_broad_category_query(text))


def strip_query_affixes(text: str) -> str:
    cleaned = normalize_user_text(text).strip().lower()
    cleaned = re.sub(r"^[\s,，.!?]+|[\s,，.!?]+$", "", cleaned)

    prefix_patterns = (
        r"^(?:น้องหลงทาง\s*)?(?:ช่วย\s*)?(?:ตามหา|ค้นหา|ค้นดู|ค้น|หา|อยากได้|ขอ|ดู|แนะนำ)",
        r"^(?:น้องหลงทาง\s*)?มี",
    )
    for _ in range(3):
        before = cleaned
        for pattern in prefix_patterns:
            cleaned = re.sub(pattern, "", cleaned).strip()
        if cleaned == before:
            break

    suffix_patterns = (
        r"(?:มีไหม|มีมั้ย|ไหม|มั้ย|หรือเปล่า|รึเปล่า|บ้างไหม|บ้างมั้ย|หน่อยสิ|หน่อย|ครับ|ค่ะ|คะ|นะ|สิ)$",
        r"(?:บ้าง)$",
    )
    for _ in range(3):
        before = cleaned
        for pattern in suffix_patterns:
            cleaned = re.sub(pattern, "", cleaned).strip()
        if cleaned == before:
            break
    return cleaned


def product_query_terms(text: str, constraints: SearchConstraints | dict[str, Any]) -> list[str]:
    text = normalize_user_text(text)
    if isinstance(constraints, dict) and constraints.get("broad_category_query"):
        return []

    quoted_terms = extract_quoted_terms(text)
    if quoted_terms:
        return quoted_terms[:5]

    brand = extract_explicit_brand(text)
    if brand:
        return [brand]

    cleaned = query_terms_filter_text(strip_query_affixes(text))
    cleaned = re.sub(r"\d+(?:\.\d+)?", " ", cleaned)
    cleaned = re.sub(r"[^\wก-๙\s]", " ", cleaned, flags=re.UNICODE)

    removable = set(GENERIC_QUERY_PHRASES) | set(BROAD_CATEGORY_WORDS)
    category = constraints.get("category") if isinstance(constraints, dict) else None
    if category:
        removable.add(str(category))

    for phrase in sorted((item for item in removable if len(item.strip()) > 2), key=lambda item: (len(item), item), reverse=True):
        cleaned = cleaned.replace(phrase.lower(), " ")

    token_stopwords = {item.lower() for item in removable}
    tokens = [
        token.strip()
        for token in cleaned.split()
        if len(token.strip()) >= 2 and not token.strip().isdigit() and token.strip() not in token_stopwords
    ]
    deduped: list[str] = []
    for token in tokens:
        if token not in deduped:
            deduped.append(token)
    return deduped[:5]


def text_for_relevance(product: Product, *, brand_only: bool = False) -> str:
    keys = ("brand",) if brand_only else ("name", "brand", "category", "description")
    return " ".join(str(product.get(key) or "") for key in keys)


def term_matches_product(term: str, product: Product, *, brand_only: bool = False) -> bool:
    normalized_term = normalize_match_text(term)
    if not normalized_term:
        return True

    normalized_product = normalize_match_text(text_for_relevance(product, brand_only=brand_only))
    if normalized_term and normalized_term in normalized_product:
        return True

    for synonym in TERM_SYNONYMS.get(term.strip().lower(), ()):
        if normalize_match_text(synonym) in normalized_product:
            return True

    tokens = significant_tokens(term)
    if not tokens:
        return False
    matched = sum(1 for token in tokens if normalize_match_text(token) in normalized_product)
    required = max(1, int(len(tokens) * 0.75))
    return matched >= required


def has_strict_product_signal(text: str) -> bool:
    return bool(extract_quoted_terms(text) or extract_explicit_brand(text))


def filter_by_strict_product_signal(products: list[Product], text: str) -> list[Product]:
    quoted_terms = extract_quoted_terms(text)
    brand = extract_explicit_brand(text)
    if not quoted_terms and not brand:
        return products

    filtered: list[Product] = []
    for product in products:
        if brand and not term_matches_product(brand, product, brand_only=True):
            continue
        if quoted_terms and not any(term_matches_product(term, product) for term in quoted_terms):
            continue
        filtered.append(product)
    return filtered


def filter_by_query_terms(products: list[Product], text: str, constraints: SearchConstraints) -> list[Product]:
    filtered = filter_by_strict_product_signal(products, text)
    terms = product_query_terms(text, constraints)
    if not terms:
        return filtered

    if detects_multi_product_query(text, terms):
        return [product for product in filtered if any(term_matches_product(term, product) for term in terms)]

    return [product for product in filtered if all(term_matches_product(term, product) for term in terms)]


def detects_multi_product_query(text: str, terms: list[str]) -> bool:
    if len(terms) < 2:
        return False
    normalized = normalize_user_text(text)
    return bool(re.search(r"(?:\s|^)(?:กับ|และ|,|，|/)(?:\s|$)", normalized))


APPAREL_NAME_KEYWORDS: tuple[str, ...] = (
    "เสื้อ",
    "กางเกง",
    "กระโปรง",
    "เดรส",
    "ชุด",
    "ถุงเท้า",
)


def filter_clothing_wear_intent(products: list[Product], text: str, constraints: SearchConstraints) -> list[Product]:
    if constraints.get("category") != "เสื้อผ้า":
        return products

    normalized = normalize_user_text(text)
    wear_markers = ("ใส่", "สวม", "แต่งตัว", "สบาย", "ไม่ร้อน", "คลายร้อน", "ผ้าโปร่ง")
    if not any(marker in normalized for marker in wear_markers):
        return products

    filtered = [
        product
        for product in products
        if any(keyword in str(product.get("name") or "") for keyword in APPAREL_NAME_KEYWORDS)
    ]
    if not filtered:
        return products

    def score(product: Product) -> int:
        name = str(product.get("name") or "")
        description = str(product.get("description") or "")
        haystack = f"{name} {description}"
        value = 0
        if "สบาย" in normalized and "สบาย" in haystack:
            value += 5
        if "ไม่ร้อน" in normalized and "ไม่ร้อน" in haystack:
            value += 6
        if "ร้อน" in normalized and any(keyword in haystack for keyword in ("คลายร้อน", "อากาศร้อน", "ร้อนๆ")):
            value += 4
        if any(keyword in haystack for keyword in ("ผ้าโปร่ง", "บางๆ", "ขาสั้น")):
            value += 3
        if any(keyword in name for keyword in ("เสื้อสายเดี่ยว", "เสื้อเชิ้ตแขนสั้น", "กางเกงขาสั้น")):
            value += 2
        if "ร้อน" in normalized and any(keyword in name for keyword in ("ยีนส์", "กันหนาว")):
            value -= 3
        return value

    return sorted(filtered, key=score, reverse=True)


async def search_products(
    query: str,
    constraints: SearchConstraints,
    top_k: int,
) -> list[Product]:
    query_embedding = await asyncio.to_thread(embed_query, query)
    if not use_supabase_backend():
        rows = await asyncio.to_thread(
            search_products_postgres,
            table_name(),
            query_embedding,
            constraints,
            top_k,
            keyword_for_search(query, constraints),
        )
        return [normalize_product(item) for item in rows]

    client = get_supabase_client()
    if (
        constraints.get("stock_status") == "out_of_stock"
        or constraints.get("min_stock") is not None
        or constraints.get("max_stock") is not None
    ):
        return await fallback_search_products(client, query, constraints, top_k)

    params = {
        "query_embedding": query_embedding,
        "match_count": top_k,
        "filter_category": constraints.get("category"),
        "min_price": constraints.get("min_price"),
        "max_price": constraints.get("max_price"),
        "in_stock_only": bool(constraints.get("stock_status") == "in_stock" or constraints.get("in_stock_only", False)),
        "keyword": keyword_for_search(query, constraints),
    }

    try:
        response = client.rpc("match_products", params).execute()
        return [normalize_product(item) for item in response.data or []]
    except Exception:
        return await fallback_search_products(client, query, constraints, top_k)


async def fallback_search_products(
    client: Any,
    query: str,
    constraints: SearchConstraints,
    top_k: int,
) -> list[Product]:
    def run_query() -> list[dict[str, Any]]:
        request = client.table(table_name()).select(PRODUCT_SELECT_COLUMNS)
        if constraints.get("category"):
            request = request.eq("category", constraints["category"])
        if constraints.get("min_price") is not None:
            request = request.gte("price", constraints["min_price"])
        if constraints.get("max_price") is not None:
            request = request.lte("price", constraints["max_price"])
        stock_status = constraints.get("stock_status")
        if stock_status == "out_of_stock":
            request = request.lte("stock_quantity", 0)
        elif stock_status == "in_stock" or constraints.get("in_stock_only"):
            request = request.gt("stock_quantity", 0)
        if constraints.get("min_stock") is not None:
            request = request.gte("stock_quantity", int(constraints["min_stock"]))
        if constraints.get("max_stock") is not None:
            request = request.lte("stock_quantity", int(constraints["max_stock"]))
        return request.limit(max(top_k * 4, 20)).execute().data or []

    rows = await asyncio.to_thread(run_query)
    query_terms = set(keyword_for_search(query, constraints).lower().split())

    def score(row: dict[str, Any]) -> int:
        text = " ".join(str(row.get(key) or "").lower() for key in ("name", "brand", "category", "description"))
        return sum(1 for term in query_terms if term and term in text)

    ranked = sorted(rows, key=score, reverse=True)[:top_k]
    return [normalize_product(item) for item in ranked]


async def search_filter_node(state: MallState, config: Optional[RunnableConfig] = None) -> MallState:
    user_text = latest_user_text(state)
    callbacks = _callbacks_from_config(config)
    deterministic = deterministic_constraints(user_text)
    if os.getenv("USE_LLM_CONSTRAINTS", "true").strip().lower() in {"1", "true", "yes", "on"}:
        try:
            extracted = await llm_constraints(user_text, callbacks)
        except Exception:
            extracted = {"in_stock_only": False}
    else:
        extracted = {"in_stock_only": False}

    constraints = merge_constraints(deterministic, extracted)
    constraints = sanitize_constraints_for_text(constraints, user_text)
    constraints = inherit_followup_constraints(constraints, state.get("constraints"), user_text)
    previous_results = state.get("validated_results", [])
    lookup_ids = parse_product_ids_for_lookup(user_text)
    if lookup_ids:
        products = await fetch_products_by_ids(lookup_ids)
        context = {
            "query": user_text,
            "constraints": constraints,
            "lookup_ids": lookup_ids,
            "result_count": len(products),
            "source": "product_id_lookup",
        }
        return {
            "search_results": products,
            "constraints": constraints,
            "current_context": json.dumps(context, ensure_ascii=False),
            "shopping_list": state.get("shopping_list", []),
        }

    if detects_stock_query(user_text) and detects_stock_reference(user_text) and previous_results:
        context = {
            "query": user_text,
            "constraints": constraints,
            "result_count": len(previous_results),
            "source": "previous_validated_results",
        }
        return {
            "search_results": previous_results,
            "constraints": constraints,
            "current_context": json.dumps(context, ensure_ascii=False),
            "shopping_list": state.get("shopping_list", []),
        }

    top_k = int(os.getenv("TOP_K_PRODUCTS", "8"))
    requested_limit = int(constraints.get("max_results") or 0)
    if requested_limit and constraints.get("group_by") == "brand":
        top_k = max(top_k, requested_limit * 8)
    elif requested_limit:
        multiplier = 8 if constraints.get("broad_category_query") or constraints.get("diversify_results") else 1
        top_k = max(top_k, requested_limit * multiplier)
    elif constraints.get("stock_query"):
        top_k = max(top_k, int(os.getenv("TOP_K_STOCK_QUERY_PRODUCTS", "500")))
    elif constraints.get("broad_category_query"):
        top_k = max(top_k, int(os.getenv("TOP_K_BROAD_CATEGORY_PRODUCTS", "500")))
    elif detects_multi_product_query(user_text, product_query_terms(user_text, constraints)):
        top_k = max(top_k, int(os.getenv("TOP_K_MULTI_QUERY_PRODUCTS", "120")))
    elif any(term in TERM_SYNONYMS for term in product_query_terms(user_text, constraints)):
        top_k = max(top_k, int(os.getenv("TOP_K_SYNONYM_PRODUCTS", "80")))

    try:
        products = await search_products(user_text, constraints, top_k)
        context = {
            "query": user_text,
            "constraints": constraints,
            "result_count": len(products),
        }
    except Exception as exc:
        products = []
        context = {
            "query": user_text,
            "constraints": constraints,
            "error": str(exc),
        }

    return {
        "search_results": products,
        "constraints": constraints,
        "current_context": json.dumps(context, ensure_ascii=False),
        "shopping_list": state.get("shopping_list", []),
    }


def product_results_table(products: list[Product]) -> str:
    rows = [
        "| ID | สินค้า | แบรนด์ | หมวด | ราคา | คงเหลือ | ตำแหน่ง |",
        "|---:|---|---|---|---:|---:|---|",
    ]
    for product in products:
        rows.append(
            f"| {product['id']} | {product.get('name', '-')} | {product.get('brand', '-')} | "
            f"{product.get('category', '-')} | {float(product.get('price') or 0):,.2f} | "
            f"{int(product.get('stock_quantity') or 0)} | {product.get('formatted_location', '-')} |"
        )
    return "\n".join(rows)


def stock_unit_for_text(text: str) -> str:
    for unit in ("ถุง", "ชิ้น", "อัน", "ตัว", "เครื่อง", "หน่วย"):
        if unit in text:
            return unit
    return "หน่วย"


def stock_answer_summary(products: list[Product], text: str, constraints: SearchConstraints) -> str:
    unit = stock_unit_for_text(text)
    total_stock = sum(int(product.get("stock_quantity") or 0) for product in products)
    if len(products) == 1:
        product = products[0]
        return (
            f"{product.get('name', 'สินค้านี้')} (ID {product.get('id', '-')}) "
            f"คงเหลือ {int(product.get('stock_quantity') or 0)} {unit}ครับ"
        )

    if "แบรนด์" in text or "ยี่ห้อ" in text or constraints.get("group_by") == "brand":
        brand_totals: dict[str, int] = {}
        for product in products:
            brand = str(product.get("brand") or "ไม่ระบุแบรนด์")
            brand_totals[brand] = brand_totals.get(brand, 0) + int(product.get("stock_quantity") or 0)
        parts = [f"{brand} {quantity} {unit}" for brand, quantity in sorted(brand_totals.items())]
        prefix = "สรุปคงเหลือตามแบรนด์: "
        if detects_stock_reference(text) and len(brand_totals) > 1:
            prefix = "จากผลล่าสุดมีหลายแบรนด์ น้องสรุปทุกแบรนด์ให้ก่อนนะครับ: "
        return f"{prefix}{', '.join(parts)} รวมทั้งหมด {total_stock} {unit}ครับ"

    return f"รวมคงเหลือ {total_stock} {unit} จาก {len(products)} รายการครับ"


def product_family_key(product: Product) -> str:
    name = str(product.get("name") or "").lower()
    variant_patterns = (
        r"\s+(?:แพ็คคู่|ขนาดเล็ก|ขนาดใหญ่|รสชาติใหม่|รุ่นมาตรฐาน|รุ่นโปร|สีขาว|สีดำ|รีฟิล|สุดคุ้ม)$",
        r"\s+แบบ\S+$",
    )
    changed = True
    while changed:
        before = name
        for pattern in variant_patterns:
            name = re.sub(pattern, "", name).strip()
        changed = name != before
    brand = str(product.get("brand") or "").strip().lower()
    return f"{brand}|{normalize_match_text(name)}"


def product_section_key(product: Product) -> str:
    location = product.get("location_info", {}) or {}
    if not isinstance(location, dict):
        return "unknown"
    zone = str(location.get("zone") or "")
    section = str(location.get("section") or "")
    return f"{zone}:{section}" if zone or section else "unknown"


def diversify_products(products: list[Product], max_results: int) -> list[Product]:
    if max_results <= 0:
        return products

    buckets: dict[str, list[Product]] = {}
    for product in products:
        buckets.setdefault(product_section_key(product), []).append(product)

    selected: list[Product] = []
    seen_families: set[str] = set()
    bucket_keys = sorted(buckets)
    positions = {key: 0 for key in bucket_keys}
    while len(selected) < max_results and bucket_keys:
        progressed = False
        for key in list(bucket_keys):
            bucket = buckets[key]
            while positions[key] < len(bucket):
                product = bucket[positions[key]]
                family = product_family_key(product)
                positions[key] += 1
                if family in seen_families:
                    continue
                selected.append(product)
                seen_families.add(family)
                progressed = True
                break
            if len(selected) >= max_results:
                break
        if not progressed:
            break

    if len(selected) < max_results:
        for product in products:
            if product in selected:
                continue
            selected.append(product)
            if len(selected) >= max_results:
                break
    return selected


def apply_result_shape(products: list[Product], constraints: SearchConstraints) -> list[Product]:
    max_results = int(constraints.get("max_results") or 0)
    group_by = constraints.get("group_by")

    if group_by == "brand":
        limit = max_results or int(os.getenv("DEFAULT_BRAND_RECOMMENDATION_LIMIT", "5"))
        unique: list[Product] = []
        seen_brands: set[str] = set()
        for product in products:
            brand = str(product.get("brand") or "").strip().lower()
            if not brand or brand in seen_brands:
                continue
            seen_brands.add(brand)
            unique.append(product)
            if limit and len(unique) >= limit:
                break
        return unique

    if max_results:
        if constraints.get("broad_category_query") or constraints.get("diversify_results"):
            return diversify_products(products, max_results)
        return products[:max_results]
    if constraints.get("broad_category_query"):
        return diversify_products(products, int(os.getenv("BROAD_CATEGORY_DISPLAY_LIMIT", "12")))
    return products


def result_intro(products: list[Product], constraints: SearchConstraints) -> str:
    requested_limit = int(constraints.get("max_results") or 0)
    group_by = constraints.get("group_by")
    stock_status = constraints.get("stock_status")

    if group_by == "brand":
        found = len({str(product.get("brand") or "").strip().lower() for product in products if product.get("brand")})
        if requested_limit and found < requested_limit:
            stock_text = "ที่สต็อกเหลือ 0" if stock_status == "out_of_stock" else "ในสต็อก"
            return f"น้องหลงทางเจอแบรนด์{stock_text} {found} แบรนด์จากที่ขอ {requested_limit} แบรนด์ครับ"
        if requested_limit:
            return f"น้องหลงทางคัดมาให้ {requested_limit} แบรนด์ตามที่ขอครับ"
        if stock_status == "out_of_stock":
            return "น้องหลงทางคัดแบรนด์ที่สต็อกเหลือ 0 ให้แล้วครับ"
        return "น้องหลงทางคัดแบรนด์ที่มีของในสต็อกให้แล้วครับ"

    if stock_status == "out_of_stock":
        return "น้องหลงทางเจอสินค้าที่สต็อกเหลือ 0 ตามคำค้นครับ"
    if constraints.get("max_stock") is not None or constraints.get("min_stock") is not None:
        return "น้องหลงทางเช็กสินค้าตามเงื่อนไขจำนวนสต็อกให้แล้วครับ"
    if constraints.get("stock_query"):
        return "น้องหลงทางเช็กจำนวนคงเหลือให้แล้วครับ"
    if requested_limit:
        return f"น้องหลงทางคัดมาให้ {len(products)} รายการตามที่ขอครับ"
    if constraints.get("broad_category_query") and constraints.get("category"):
        return f"น้องหลงทางคัดตัวอย่างสินค้าในหมวด{constraints['category']}แบบหลายชนิดให้แล้วครับ"
    if constraints.get("max_price") is not None or constraints.get("min_price") is not None:
        return "น้องหลงทางคัดสินค้าตามงบและเงื่อนไขราคาให้แล้วครับ"
    return "น้องหลงทางเจอสินค้าในสต็อกให้แล้วครับ"


async def navigation_stock_node(state: MallState, config: Optional[RunnableConfig] = None) -> MallState:
    del config
    user_text = latest_user_text(state)
    products = state.get("search_results", [])
    constraints = state.get("constraints", {})
    stock_status = constraints.get("stock_status")
    include_zero_for_count = (
        bool(constraints.get("stock_query"))
        and stock_status is None
        and constraints.get("min_stock") is None
        and constraints.get("max_stock") is None
    )
    eligible: list[Product] = []
    for product in products:
        stock_quantity = int(product.get("stock_quantity") or 0)
        if stock_status == "out_of_stock":
            if stock_quantity > 0:
                continue
        elif not include_zero_for_count:
            if stock_quantity <= 0:
                continue
        enriched = dict(product)
        enriched["formatted_location"] = format_location(product.get("location_info", {}))
        eligible.append(enriched)  # type: ignore[arg-type]

    eligible = filter_by_query_terms(eligible, user_text, constraints)
    eligible = filter_clothing_wear_intent(eligible, user_text, constraints)
    shaped_results = apply_result_shape(eligible, constraints)

    if not shaped_results:
        content = (
            f"{NOT_FOUND_TEXT}\n\n"
            f"{CATCHPHRASE} ลองบอกหมวดใน 5 หมวดนี้ได้ครับ: "
            f"{', '.join(ALLOWED_CATEGORIES)}"
        )
        return {
            "messages": [AIMessage(content=content)],
            "validated_results": [],
            "current_context": NOT_FOUND_TEXT,
            "shopping_list": state.get("shopping_list", []),
        }

    display_results = shaped_results
    truncated_note = ""
    if constraints.get("stock_query") and not constraints.get("max_results"):
        display_limit = int(os.getenv("STOCK_QUERY_DISPLAY_LIMIT", "30"))
        if display_limit > 0 and len(shaped_results) > display_limit:
            display_results = shaped_results[:display_limit]
            truncated_note = f"แสดง {len(display_results)} รายการแรกจากทั้งหมด {len(shaped_results)} รายการครับ\n\n"

    table = product_results_table(display_results)
    intro = result_intro(shaped_results, constraints)
    stock_summary = ""
    if constraints.get("stock_query"):
        stock_summary = f"{stock_answer_summary(shaped_results, user_text, constraints)}\n\n"
    content = (
        f"{CATCHPHRASE} {intro}\n\n"
        f"{stock_summary}"
        f"{table}\n\n"
        f"{truncated_note}"
        "ถ้าจะเก็บไว้ในลิสต์ พิมพ์ `เพิ่ม <ID>` เช่น `เพิ่ม 12` "
        "หรือพิมพ์ `สรุปเส้นทาง` เพื่อให้น้องเรียงทางเดินให้ครับ\n\n"
        f"🗺️ **[ดูตำแหน่งใน 3D Navigator](/public/model_viewer.html)** ({len(display_results)} รายการ)"
    )
    return {
        "messages": [AIMessage(content=content)],
        "validated_results": display_results,
        "current_context": json.dumps(display_results, ensure_ascii=False),
        "shopping_list": state.get("shopping_list", []),
    }


def has_add_request(text: str) -> bool:
    return bool(re.search(r"(?:เพิ่ม|หยิบ|เอา|ใส่(?:รถเข็น|ตะกร้า)|ลงตะกร้า|\badd\b)", text, flags=re.IGNORECASE))


def strip_quantity_phrases(text: str) -> str:
    return re.sub(r"(?:จำนวน\s*)?\d+\s*(?:ชิ้น|เครื่อง|อัน|ตัว|ถุง|หน่วย)", " ", text)


def is_numeric_id_list_segment(segment: str) -> bool:
    cleaned = strip_quantity_phrases(segment.lower())
    cleaned = re.sub(
        r"(?:เพิ่ม|หยิบ|เอา|ใส่(?:รถเข็น|ตะกร้า)|ลงตะกร้า|add|สินค้า|รายการ|หมายเลข|เลข|เบอร์|id|รหัส(?:สินค้า)?|และ|กับ|อย่างละ|ทุกอัน|ทุกตัว|ทุกชิ้น|ทั้งหมด)",
        " ",
        cleaned,
        flags=re.IGNORECASE,
    )
    cleaned = re.sub(r"[\d\s,，#\-–—]+", " ", cleaned)
    return not cleaned.strip()


def dedupe_ids(values: Iterable[int]) -> list[int]:
    ids: list[int] = []
    for value in values:
        if value not in ids:
            ids.append(value)
    return ids


def parse_product_ids_for_add(text: str, valid_ids: Optional[set[int]] = None) -> list[int]:
    if re.search(r"(?:อันแรก|ตัวแรก|ชิ้นแรก|รายการแรก|first)", text, flags=re.IGNORECASE):
        return []
    if not has_add_request(text):
        return []

    explicit_ids = [
        int(match.group(1))
        for match in re.finditer(r"(?:id|ID|รหัส(?:สินค้า)?|หมายเลข|เลข)\s*#?\s*(\d+)", text, flags=re.IGNORECASE)
    ]
    if explicit_ids:
        return dedupe_ids(explicit_ids)

    command_match = re.search(r"(?:เพิ่ม|หยิบ|เอา|ใส่(?:รถเข็น|ตะกร้า)|ลงตะกร้า|\badd\b)(.*)$", text, flags=re.IGNORECASE)
    segment = command_match.group(1) if command_match else text
    if not is_numeric_id_list_segment(segment):
        return []

    cleaned = strip_quantity_phrases(segment)
    values = [int(match.group(0)) for match in re.finditer(r"\d+", cleaned)]
    if valid_ids:
        values = [value for value in values if value in valid_ids]
    return dedupe_ids(values)


def parse_quantity_for_add(text: str) -> int:
    match = re.search(r"(?:จำนวน\s*)?(\d+)\s*(?:ชิ้น|เครื่อง|อัน|ตัว|ถุง|หน่วย)", text)
    if not match:
        return 1
    quantity = int(match.group(1))
    return max(1, quantity)


def extract_add_target_text(text: str) -> str:
    if not has_add_request(text):
        return ""

    command_match = re.search(
        r"(?:เพิ่ม|หยิบ|เอา|ใส่(?:รถเข็น|ตะกร้า)|ลงตะกร้า)(.*)$",
        text,
        flags=re.IGNORECASE,
    )
    segment = command_match.group(1) if command_match else text
    cleaned = re.sub(
        r"(?:จำนวน\s*\d+\s*(?:ชิ้น|เครื่อง|อัน|ตัว|ถุง|หน่วย)|อีก\s*\d+\s*(?:ชิ้น|เครื่อง|อัน|ตัว|ถุง|หน่วย)|\d+\s*(?:ชิ้น|เครื่อง|อัน|ตัว|ถุง|หน่วย)|(?:id|ID|รหัส(?:สินค้า)?|หมายเลข|เลข)\s*#?\s*\d+)",
        " ",
        segment,
        flags=re.IGNORECASE,
    )
    cleaned = re.sub(r"[\s,，]+", " ", cleaned).strip()
    if not cleaned or cleaned.lower() in {"ทั้งหมด", "ทุกอัน", "ทุกตัว", "ทุกชิ้น", "ทุกรายการ"}:
        return ""
    return cleaned


def detects_price_override_request(text: str) -> bool:
    return bool(re.search(r"(?:ติดลบ|ราคาติดลบ|ส่วนลด|ลดราคาเอง|ฟรี|ศูนย์บาท)", text, flags=re.IGNORECASE))


def wants_summary(text: str) -> bool:
    return any(keyword in text.lower() for keyword in ("สรุป", "checkout", "เช็คเอาท์", "คิดเงิน", "เส้นทาง", "route"))


def wants_first_result(text: str) -> bool:
    return bool(re.search(r"(?:อันแรก|ตัวแรก|ชิ้นแรก|รายการแรก|first)", text, flags=re.IGNORECASE))


def wants_all_results(text: str) -> bool:
    return has_add_request(text) and bool(
        re.search(r"(?:ทั้งหมด|ทุกอัน|ทุกตัว|ทุกชิ้น|ทุกรายการ|all)", text, flags=re.IGNORECASE)
    )


def parse_result_positions_for_add(text: str) -> list[int]:
    if not has_add_request(text):
        return []
    positions: list[int] = []
    patterns = (
        r"(?:รายการ|อัน|ตัว|ชิ้น)\s*ที่\s*(\d+)",
        r"(?:ที่)\s*(\d+)",
    )
    for pattern in patterns:
        for match in re.finditer(pattern, text, flags=re.IGNORECASE):
            position = int(match.group(1))
            if position > 0 and position not in positions:
                positions.append(position)
    return positions


async def fetch_products_by_ids(product_ids: list[int]) -> list[Product]:
    if not product_ids:
        return []

    unique_ids = sorted(set(int(pid) for pid in product_ids))

    if not use_supabase_backend():
        rows = await asyncio.to_thread(fetch_products_by_ids_postgres, table_name(), unique_ids)
        products = [normalize_product(row) for row in rows]
        for product in products:
            product["formatted_location"] = format_location(product.get("location_info", {}))
        return products

    def run_query() -> list[dict[str, Any]]:
        request = get_supabase_client().table(table_name()).select(PRODUCT_SELECT_COLUMNS)
        try:
            return request.in_("id", unique_ids).execute().data or []
        except AttributeError:
            values = "(" + ",".join(map(str, unique_ids)) + ")"
            return request.filter("id", "in", values).execute().data or []

    rows = await asyncio.to_thread(run_query)
    products = [normalize_product(row) for row in rows]
    for product in products:
        product["formatted_location"] = format_location(product.get("location_info", {}))
    return products


async def cart_route_node(state: MallState, config: Optional[RunnableConfig] = None) -> MallState:
    del config
    user_text = latest_user_text(state)
    shopping_list = list(state.get("shopping_list", []))
    previous_results = state.get("validated_results", [])
    product_ids = parse_product_ids_for_add(user_text)
    requested_quantity = parse_quantity_for_add(user_text)
    add_target_text = extract_add_target_text(user_text)

    if wants_all_results(user_text) and previous_results:
        product_ids = [int(product["id"]) for product in previous_results if "id" in product]
    elif wants_first_result(user_text) and previous_results:
        product_ids = [int(previous_results[0]["id"])]
    elif not product_ids and previous_results:
        positions = parse_result_positions_for_add(user_text)
        if positions:
            product_ids = [
                int(previous_results[position - 1]["id"])
                for position in positions
                if 0 < position <= len(previous_results) and "id" in previous_results[position - 1]
            ]

    if not product_ids and add_target_text:
        if previous_results:
            matched = filter_by_query_terms(previous_results, add_target_text, state.get("constraints", {}))
            if matched:
                product_ids = [int(matched[0]["id"])]

        if not product_ids:
            search_candidates = await search_products(add_target_text, state.get("constraints", {}), top_k=5)
            for candidate in search_candidates:
                if term_matches_product(add_target_text, candidate):
                    product_ids = [int(candidate["id"])]
                    break

    added_products: list[Product] = []
    rejected_messages: list[str] = []
    if product_ids:
        products = await fetch_products_by_ids(product_ids)
        products_by_id = {int(product["id"]): product for product in products}
        for pid in product_ids:
            product = products_by_id.get(pid)
            if not product:
                rejected_messages.append(f"ไม่พบ ID {pid}")
                continue
            stock = int(product.get("stock_quantity") or 0)
            if stock <= 0:
                rejected_messages.append(f"ID {pid} หมดสต็อก")
                continue

            quantity = requested_quantity
            already_in_cart = sum(1 for item_id in shopping_list if int(item_id) == pid)
            if already_in_cart + quantity > stock:
                rejected_messages.append(f"ID {pid} มีคงเหลือ {stock} ชิ้น เพิ่ม {quantity} ชิ้นไม่ได้")
                continue

            for _ in range(quantity):
                shopping_list = add_to_cart_state(shopping_list, pid)
            added_products.append(product)

    if wants_summary(user_text):
        products = await fetch_products_by_ids(shopping_list)
        summary = summarize_route(products, shopping_list)
        return {
            "messages": [AIMessage(content=summary.markdown)],
            "shopping_list": shopping_list,
            "current_context": f"route_summary total={summary.total_price} count={summary.item_count}",
        }

    if added_products:
        quantity_note = f" จำนวน {requested_quantity} ชิ้น" if requested_quantity > 1 and len(added_products) == 1 else ""
        multi_quantity_note = f" อย่างละ {requested_quantity} ชิ้น" if requested_quantity > 1 and len(added_products) > 1 else ""
        names = ", ".join(f"{product['name']} (ID {product['id']}){quantity_note}" for product in added_products)
        content = (
            f"{CATCHPHRASE} น้องหลงทางเพิ่มให้ในลิสต์แล้วครับ{multi_quantity_note}: {names}\n\n"
            "พิมพ์ `สรุปเส้นทาง` ได้เลยถ้าพร้อมเดินซื้อของ"
        )
        if rejected_messages:
            content += "\n\nรายการที่ไม่ได้เพิ่ม:\n" + "\n".join(f"- {message}" for message in rejected_messages)
        if detects_price_override_request(user_text):
            content += "\n\nราคาจะใช้จากฐานข้อมูลสินค้าเท่านั้น น้องไม่สามารถตั้งราคาเป็นติดลบหรือแก้ส่วนลดเองได้ครับ"
    elif rejected_messages:
        content = f"{NOT_FOUND_TEXT}\n\n" + "\n".join(f"- {message}" for message in rejected_messages)
    else:
        content = NEED_PRODUCT_ID_TEXT

    return {
        "messages": [AIMessage(content=content)],
        "shopping_list": shopping_list,
        "current_context": "cart_updated",
    }


async def general_node(state: MallState, config: Optional[RunnableConfig] = None) -> MallState:
    del config
    user_text = latest_user_text(state)
    direct_response = deterministic_direct_response(user_text)
    content = direct_response or deterministic_general_response(user_text)
    return {
        "messages": [AIMessage(content=content)],
        "shopping_list": state.get("shopping_list", []),
        "current_context": "deterministic_general",
    }


async def direct_response_node(state: MallState, config: Optional[RunnableConfig] = None) -> MallState:
    del config
    content = state.get("direct_response") or deterministic_direct_response(latest_user_text(state)) or OUT_OF_SCOPE_TEXT
    return {
        "messages": [AIMessage(content=content)],
        "shopping_list": state.get("shopping_list", []),
        "current_context": "deterministic_guard",
        "constraints": {},
        "search_results": [],
        "validated_results": [],
    }


def build_graph():
    workflow = StateGraph(MallState)
    workflow.add_node("supervisor", supervisor_node)
    workflow.add_node("search_filter", search_filter_node)
    workflow.add_node("navigation_stock", navigation_stock_node)
    workflow.add_node("cart_route", cart_route_node)
    workflow.add_node("general", general_node)
    workflow.add_node("direct", direct_response_node)

    workflow.add_edge(START, "supervisor")
    workflow.add_conditional_edges(
        "supervisor",
        route_after_supervisor,
        {
            "search": "search_filter",
            "cart": "cart_route",
            "general": "general",
            "direct": "direct",
        },
    )
    workflow.add_edge("search_filter", "navigation_stock")
    workflow.add_edge("navigation_stock", END)
    workflow.add_edge("cart_route", END)
    workflow.add_edge("general", END)
    workflow.add_edge("direct", END)
    return workflow.compile(checkpointer=MemorySaver())


@lru_cache(maxsize=1)
def get_compiled_graph():
    return build_graph()
