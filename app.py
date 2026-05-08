from __future__ import annotations

import os
from typing import Any

import chainlit as cl
from langchain_core.callbacks import AsyncCallbackHandler
from langchain_core.messages import AIMessage, HumanMessage

try:
    from langchain.memory import ConversationBufferMemory
except ImportError:  # pragma: no cover - LangChain 1.x compatibility
    from langchain_classic.memory import ConversationBufferMemory

from agents import get_compiled_graph
from graph_state import ALLOWED_CATEGORIES, CATCHPHRASE


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


def last_ai_content(messages: list[Any]) -> str:
    for message in reversed(messages):
        if isinstance(message, AIMessage):
            return str(message.content)
        if isinstance(message, dict) and message.get("role") in {"assistant", "ai"}:
            return str(message.get("content", ""))
    return ""


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
            f"บอกชื่อสินค้า งบประมาณ หรือหมวดที่อยากหาได้เลย หมวดที่น้องดูแลคือ: {categories}"
        )
    ).send()


@cl.on_message
async def on_message(message: cl.Message) -> None:
    graph = cl.user_session.get("graph") or get_compiled_graph()
    memory: ConversationBufferMemory = cl.user_session.get("memory")
    thread_id = cl.context.session.id

    graph_input: dict[str, Any] = {"messages": [HumanMessage(content=message.content)]}
    if not cl.user_session.get("initialized_graph_state"):
        graph_input["shopping_list"] = []
        graph_input["current_context"] = ""
        cl.user_session.set("initialized_graph_state", True)

    async with cl.Step(name="น้องหลงทางกำลังตรวจคำถาม...", type="tool") as step:
        step.input = message.content
        thinking_callback = ChainlitDeepSeekThinkingCallback()
        result = await graph.ainvoke(
            graph_input,
            config={
                "configurable": {"thread_id": thread_id},
                "callbacks": [thinking_callback],
            },
        )
        step.output = "ตรวจคำถาม ค้นคลังสินค้า และจัดคำตอบเรียบร้อย"

    answer = last_ai_content(result.get("messages", []))
    if not answer:
        answer = f"{CATCHPHRASE} น้องหลงทางยังตอบไม่ได้ครับ ลองถามหาสินค้าอีกครั้งได้เลย"

    if memory:
        memory.save_context({"input": message.content}, {"output": answer})

    await cl.Message(content=answer).send()


if __name__ == "__main__":
    os.system("chainlit run app.py --host 0.0.0.0 --port 8000")
