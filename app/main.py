import chainlit as cl
from agent import create_agent
from config import load_config

config = load_config()

@cl.on_chat_start
async def start():
    agent = create_agent(config)
    cl.user_session.set("agent", agent)
    cl.user_session.set("shopping_list", [])
    
    await cl.Message(
        content="🛒 สวัสดีค่า! หลงทางรึป่าว หาของไม่เจอใช่มั้ย 😊\n\nน้องหลงทางพร้อมช่วยแล้วนะ บอกมาเลยว่าอยากหาอะไร~"
    ).send()

@cl.on_message
async def main(message: cl.Message):
    agent = cl.user_session.get("agent")
    
    async with cl.Step(name="🤔 กำลังคิด...", type="tool") as step:
        response = await agent.arun(message.content)
        step.output = response
    
    await cl.Message(content=response).send()
