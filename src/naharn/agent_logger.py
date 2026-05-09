from __future__ import annotations

import json
import os
import threading
from datetime import datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

from naharn.paths import LOGS_DIR, PUBLIC_DIR

AGENT_LOG_JSON = Path(os.getenv("AGENT_LOG_JSON", PUBLIC_DIR / "agent_logs.json"))
AGENT_LOG_JSONL = Path(os.getenv("AGENT_LOG_JSONL", LOGS_DIR / "agent.log.jsonl"))
MAX_LOG_ENTRIES = int(os.getenv("AGENT_LOG_MAX_ENTRIES", "300"))

_LOCK = threading.Lock()


def new_run_id() -> str:
    return uuid4().hex[:12]


def _now_iso() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def _truncate(text: str, limit: int = 2000) -> str:
    if len(text) <= limit:
        return text
    return f"{text[:limit]}... [truncated {len(text) - limit} chars]"


def _safe_json(value: Any, depth: int = 0) -> Any:
    if depth > 4:
        return repr(value)

    if value is None or isinstance(value, bool | int | float):
        return value

    if isinstance(value, str):
        return _truncate(value)

    if isinstance(value, dict):
        result: dict[str, Any] = {}
        for index, (key, item) in enumerate(value.items()):
            if index >= 30:
                result["..."] = f"{len(value) - index} more keys"
                break
            result[str(key)] = _safe_json(item, depth + 1)
        return result

    if isinstance(value, (list, tuple, set)):
        items = list(value)
        result = [_safe_json(item, depth + 1) for item in items[:30]]
        if len(items) > 30:
            result.append(f"... {len(items) - 30} more items")
        return result

    content = getattr(value, "content", None)
    if content is not None:
        return {
            "type": value.__class__.__name__,
            "content": _safe_json(content, depth + 1),
        }

    return _truncate(repr(value))


def _last_ai_answer(messages: Any) -> str:
    if not isinstance(messages, list):
        return ""
    for message in reversed(messages):
        if isinstance(message, dict):
            role = message.get("role") or message.get("type")
            if role in {"assistant", "ai"}:
                return _truncate(str(message.get("content", "")))
            continue
        if message.__class__.__name__ == "AIMessage":
            return _truncate(str(getattr(message, "content", "")))
    return ""


def _product_summary(product: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": product.get("id"),
        "name": product.get("name"),
        "brand": product.get("brand"),
        "category": product.get("category"),
        "price": product.get("price"),
        "stock_quantity": product.get("stock_quantity"),
        "formatted_location": product.get("formatted_location"),
        "coordinates_3d": product.get("coordinates_3d"),
    }


def summarize_agent_result(result: dict[str, Any]) -> dict[str, Any]:
    search_results = result.get("search_results") or []
    validated_results = result.get("validated_results") or []
    messages = result.get("messages") or []

    return {
        "route": result.get("route"),
        "agent_plan": _safe_json(result.get("agent_plan") or {}),
        "constraints": _safe_json(result.get("constraints") or {}),
        "current_context": _safe_json(result.get("current_context") or ""),
        "search_result_count": len(search_results) if isinstance(search_results, list) else None,
        "validated_result_count": len(validated_results) if isinstance(validated_results, list) else None,
        "validated_results": [
            _product_summary(product)
            for product in validated_results[:20]
            if isinstance(product, dict)
        ],
        "shopping_list": _safe_json(result.get("shopping_list") or []),
        "answer_preview": _last_ai_answer(messages),
    }


def summarize_trace_payload(payload: Any) -> Any:
    if isinstance(payload, dict):
        summary: dict[str, Any] = {}
        for key in (
            "route",
            "agent_plan",
            "constraints",
            "current_context",
            "direct_response",
            "search_results",
            "validated_results",
            "shopping_list",
            "messages",
        ):
            if key not in payload:
                continue
            value = payload[key]
            if key in {"search_results", "validated_results"} and isinstance(value, list):
                summary[f"{key}_count"] = len(value)
                summary[key] = [
                    _product_summary(item)
                    for item in value[:10]
                    if isinstance(item, dict)
                ]
            elif key == "messages":
                summary["message_count"] = len(value) if isinstance(value, list) else None
                summary["last_answer_preview"] = _last_ai_answer(value)
            else:
                summary[key] = _safe_json(value)
        return summary or _safe_json(payload)
    return _safe_json(payload)


def append_agent_log(
    event: str,
    *,
    run_id: str,
    thread_id: str | None = None,
    level: str = "info",
    message: str = "",
    data: Any = None,
) -> dict[str, Any]:
    entry = {
        "id": uuid4().hex,
        "timestamp": _now_iso(),
        "level": level,
        "event": event,
        "run_id": run_id,
        "thread_id": thread_id,
        "message": message,
        "data": _safe_json(data or {}),
    }

    with _LOCK:
        PUBLIC_DIR.mkdir(parents=True, exist_ok=True)
        LOGS_DIR.mkdir(parents=True, exist_ok=True)

        payload = {"logs": []}
        if AGENT_LOG_JSON.exists():
            try:
                payload = json.loads(AGENT_LOG_JSON.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                payload = {"logs": []}

        logs = payload.get("logs")
        if not isinstance(logs, list):
            logs = []

        logs.append(entry)
        logs = logs[-MAX_LOG_ENTRIES:]

        temp_path = AGENT_LOG_JSON.with_suffix(".json.tmp")
        temp_path.write_text(
            json.dumps({"logs": logs}, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        temp_path.replace(AGENT_LOG_JSON)

        with AGENT_LOG_JSONL.open("a", encoding="utf-8") as file:
            file.write(json.dumps(entry, ensure_ascii=False) + "\n")

    return entry


def clear_agent_logs() -> dict[str, Any]:
    """Clear all persisted agent logs and leave the JSON feed in a valid empty state."""
    with _LOCK:
        PUBLIC_DIR.mkdir(parents=True, exist_ok=True)
        LOGS_DIR.mkdir(parents=True, exist_ok=True)

        deleted_entries = 0
        if AGENT_LOG_JSON.exists():
            try:
                payload = json.loads(AGENT_LOG_JSON.read_text(encoding="utf-8"))
                logs = payload.get("logs")
                deleted_entries = len(logs) if isinstance(logs, list) else 0
            except json.JSONDecodeError:
                deleted_entries = 0

        temp_path = AGENT_LOG_JSON.with_suffix(".json.tmp")
        temp_path.write_text(
            json.dumps({"logs": []}, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        temp_path.replace(AGENT_LOG_JSON)

        deleted_jsonl_lines = 0
        if AGENT_LOG_JSONL.exists():
            try:
                with AGENT_LOG_JSONL.open("r", encoding="utf-8") as file:
                    deleted_jsonl_lines = sum(1 for _ in file)
            except OSError:
                deleted_jsonl_lines = 0
        AGENT_LOG_JSONL.write_text("", encoding="utf-8")

    return {
        "logs": [],
        "deleted_entries": deleted_entries,
        "deleted_jsonl_lines": deleted_jsonl_lines,
    }
