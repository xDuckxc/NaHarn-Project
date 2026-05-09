from __future__ import annotations

import json
import os
from typing import Any

import chainlit as cl
from langchain_core.callbacks import AsyncCallbackHandler
from langchain_core.messages import AIMessage, HumanMessage

from naharn.agent_logger import (
    append_agent_log,
    clear_agent_logs,
    new_run_id,
    summarize_agent_result,
    summarize_trace_payload,
)

try:
    from langchain.memory import ConversationBufferMemory
except ImportError:  # pragma: no cover - LangChain 1.x compatibility
    from langchain_classic.memory import ConversationBufferMemory

from naharn.agents import get_compiled_graph
from naharn.graph_state import (
    ALLOWED_CATEGORIES,
    CATCHPHRASE,
    format_location,
    get_3d_coordinates,
    parse_location_info,
)
from naharn.paths import PROJECT_ROOT, PUBLIC_DIR

try:
    from chainlit.server import app as chainlit_server_app
except ImportError:  # pragma: no cover - available when running under Chainlit
    chainlit_server_app = None


if chainlit_server_app is not None:

    @chainlit_server_app.post("/agent-logs/clear")
    async def clear_agent_logs_endpoint() -> dict[str, Any]:
        return clear_agent_logs()


class ChainlitDeepSeekThinkingCallback(AsyncCallbackHandler):
    """Consumes DeepSeek reasoning events without exposing hidden reasoning in the UI."""

    def __init__(self) -> None:
        self.has_reasoning = False

    async def on_reasoning_delta(self, token: str, **_: Any) -> None:
        if token:
            self.has_reasoning = True

    async def on_reasoning_complete(self, reasoning: str, **_: Any) -> None:
        if reasoning and not self.has_reasoning:
            self.has_reasoning = True


class AgentLogCallback(AsyncCallbackHandler):
    """Writes high-level LangGraph trace events without storing hidden reasoning."""

    def __init__(self, *, run_id: str, thread_id: str) -> None:
        self.run_id = run_id
        self.thread_id = thread_id

    async def on_chain_start(
        self,
        serialized: dict[str, Any],
        inputs: dict[str, Any],
        *,
        run_id: Any,
        parent_run_id: Any | None = None,
        tags: list[str] | None = None,
        **_: Any,
    ) -> None:
        append_agent_log(
            "chain_start",
            run_id=self.run_id,
            thread_id=self.thread_id,
            message="LangGraph chain started",
            data={
                "chain_run_id": str(run_id),
                "parent_run_id": str(parent_run_id) if parent_run_id else None,
                "name": (serialized or {}).get("name") or (serialized or {}).get("id"),
                "tags": tags or [],
                "inputs": summarize_trace_payload(inputs),
            },
        )

    async def on_chain_end(
        self,
        outputs: dict[str, Any],
        *,
        run_id: Any,
        parent_run_id: Any | None = None,
        **_: Any,
    ) -> None:
        append_agent_log(
            "chain_end",
            run_id=self.run_id,
            thread_id=self.thread_id,
            message="LangGraph chain finished",
            data={
                "chain_run_id": str(run_id),
                "parent_run_id": str(parent_run_id) if parent_run_id else None,
                "outputs": summarize_trace_payload(outputs),
            },
        )

    async def on_chain_error(
        self,
        error: BaseException,
        *,
        run_id: Any,
        parent_run_id: Any | None = None,
        **_: Any,
    ) -> None:
        append_agent_log(
            "chain_error",
            run_id=self.run_id,
            thread_id=self.thread_id,
            level="error",
            message="LangGraph chain failed",
            data={
                "chain_run_id": str(run_id),
                "parent_run_id": str(parent_run_id) if parent_run_id else None,
                "error_type": error.__class__.__name__,
                "error": str(error),
            },
        )


def last_ai_content(messages: list[Any]) -> str:
    for message in reversed(messages):
        if isinstance(message, AIMessage):
            return str(message.content)
        if isinstance(message, dict) and message.get("role") in {"assistant", "ai"}:
            return str(message.get("content", ""))
    return ""


def _safe_mapping(value: Any) -> dict[str, Any]:
    try:
        parsed = parse_location_info(value)
    except (TypeError, ValueError, json.JSONDecodeError):
        return {}
    return parsed if isinstance(parsed, dict) else {}


def _safe_coordinates(product: dict[str, Any]) -> dict[str, float] | None:
    coordinates = _safe_mapping(product.get("coordinates_3d"))
    if not all(key in coordinates for key in ("x", "y", "z")):
        coordinates = get_3d_coordinates(product.get("location_info", {})) or {}
    try:
        return {
            "x": float(coordinates["x"]),
            "y": float(coordinates["y"]),
            "z": float(coordinates["z"]),
        }
    except (KeyError, TypeError, ValueError):
        return None


def write_pins_file(products: list[dict[str, Any]]) -> int:
    pins_data: list[dict[str, Any]] = []
    for product in products:
        if not isinstance(product, dict):
            continue
        coords = _safe_coordinates(product)
        if not coords:
            continue

        location_info = _safe_mapping(product.get("location_info"))
        location_label = product.get("formatted_location") or (
            format_location(location_info) if location_info else ""
        )
        pins_data.append(
            {
                "id": product.get("id", 0),
                "name": product.get("name", ""),
                "label": f"{product.get('name', '')} - {location_label}".strip(" -"),
                "zone": str(location_info.get("zone", "")).upper(),
                "section": str(location_info.get("section", "")),
                "shelf": str(location_info.get("shelf", "")),
                "x": coords["x"],
                "y": coords["y"],
                "z": coords["z"],
            }
        )

    PUBLIC_DIR.mkdir(parents=True, exist_ok=True)
    pins_file = PUBLIC_DIR / "pins.json"
    with pins_file.open("w", encoding="utf-8") as f:
        json.dump({"pins": pins_data}, f, ensure_ascii=False, indent=2)
    return len(pins_data)


@cl.on_chat_start
async def on_chat_start() -> None:
    memory = ConversationBufferMemory(return_messages=True, memory_key="chat_history")
    cl.user_session.set("memory", memory)
    cl.user_session.set("graph", get_compiled_graph())
    cl.user_session.set("initialized_graph_state", False)

    categories = ", ".join(ALLOWED_CATEGORIES)
    await cl.Message(
        content=(
            f"{CATCHPHRASE} น้องหลงทางพร้อมพาเดินหาของแล้วครับ\n\n"
            f"บอกชื่อสินค้า งบประมาณ หรือหมวดที่อยากหาได้เลย หมวดที่น้องดูแลคือ: {categories}\n\n"
            "ใช้คำสั่ง `เพิ่ม <ID>` เพื่อเก็บสินค้า และ `แสดงแผนที่` เพื่อเปิด pin ล่าสุดใน 3D Navigator\n\n"
            f"🗺️ **[เปิด 3D Navigator](/public/model_viewer.html)** เพื่อดูแผนที่ห้างแบบ 3 มิติ\n\n"
            f"🧾 **[ดู Agent Logs](/public/agent_logs.html)** สำหรับตรวจ trace การทำงาน"
        )
    ).send()


@cl.on_message
async def on_message(message: cl.Message) -> None:
    graph = cl.user_session.get("graph") or get_compiled_graph()
    memory: ConversationBufferMemory = cl.user_session.get("memory")
    thread_id = cl.context.session.id
    run_id = new_run_id()

    append_agent_log(
        "message_received",
        run_id=run_id,
        thread_id=thread_id,
        message="User message received",
        data={"input": message.content},
    )

    graph_input: dict[str, Any] = {"messages": [HumanMessage(content=message.content)]}
    if not cl.user_session.get("initialized_graph_state"):
        graph_input["shopping_list"] = []
        graph_input["current_context"] = ""
        cl.user_session.set("initialized_graph_state", True)

    async with cl.Step(name="น้องหลงทางกำลังตรวจคำถาม...", type="tool") as step:
        step.input = message.content
        thinking_callback = ChainlitDeepSeekThinkingCallback()
        log_callback = AgentLogCallback(run_id=run_id, thread_id=thread_id)
        try:
            result = await graph.ainvoke(
                graph_input,
                config={
                    "configurable": {"thread_id": thread_id, "trace_run_id": run_id},
                    "callbacks": [thinking_callback, log_callback],
                },
            )
        except Exception as exc:
            append_agent_log(
                "message_failed",
                run_id=run_id,
                thread_id=thread_id,
                level="error",
                message="Agent failed while handling message",
                data={"error_type": exc.__class__.__name__, "error": str(exc)},
            )
            step.output = f"เกิดข้อผิดพลาด ดูรายละเอียดที่ /public/agent_logs.html (run_id={run_id})"
            raise

        result_summary = summarize_agent_result(result)
        append_agent_log(
            "message_completed",
            run_id=run_id,
            thread_id=thread_id,
            message="Agent response completed",
            data={**result_summary, "deepseek_reasoning_observed": thinking_callback.has_reasoning},
        )
        step.output = (
            f"ตรวจคำถาม ค้นคลังสินค้า และจัดคำตอบเรียบร้อย\n\n"
            f"run_id: `{run_id}`\n"
            f"route: `{result_summary.get('route')}`\n"
            f"ผลลัพธ์ที่แสดง: {result_summary.get('validated_result_count') or 0} รายการ\n\n"
            f"DeepSeek reasoning stream: `{'observed' if thinking_callback.has_reasoning else 'not observed'}`\n\n"
            f"[เปิด Agent Logs](/public/agent_logs.html)"
        )

    answer = last_ai_content(result.get("messages", []))
    if not answer:
        answer = f"{CATCHPHRASE} น้องหลงทางยังตอบไม่ได้ครับ ลองถามหาสินค้าอีกครั้งได้เลย"

    if memory:
        memory.save_context({"input": message.content}, {"output": answer})

    await cl.Message(content=answer).send()
    
    # Write pins data to JSON file for 3D viewer.
    route = result_summary.get("route")
    validated_results = result.get("validated_results", [])
    if route in {"search", "cart", "map"}:
        pin_count = write_pins_file(validated_results if isinstance(validated_results, list) else [])
        append_agent_log(
            "pins_written",
            run_id=run_id,
            thread_id=thread_id,
            message="3D pins file updated",
            data={"pin_count": pin_count, "route": route},
        )


if __name__ == "__main__":
    src_dir = PROJECT_ROOT / "src"
    os.environ["PYTHONPATH"] = f"{src_dir}{os.pathsep}{os.environ.get('PYTHONPATH', '')}".rstrip(os.pathsep)
    os.system(f"chainlit run {src_dir / 'naharn' / 'app.py'} --host 0.0.0.0 --port 8000")
