from langchain.agents import AgentExecutor, create_openai_functions_agent
from langchain.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain.memory import ConversationBufferMemory
from langchain_openai import ChatOpenAI
from config import Config
from database import SupaBaseDB
from embeddings import EmbeddingService
from tools import SemanticSearchTool
from tools2 import StockCheckerTool
from tools3 import NavigationTool
from tools4 import ShoppingListTool, RoutePlannerTool

SYSTEM_PROMPT = """คุณคือ "น้องหลงทาง" ผู้ช่วยช้อปปิ้งที่ขี้เล่นและกระตือรือร้น

บุคลิก:
- ใช้คำติดปาก "หลงทางรึป่าว หาของไม่เจอใช่มั้ย" เป็นครั้งคราว
- พูดจาเป็นกันเอง ใช้ "ค่ะ" "นะ" "เลย"
- กระตือรือร้นช่วยเหลือและให้คำแนะนำ

กฎเหล็ก:
1. ตอบเฉพาะเรื่องสินค้า 5 หมวด: อาหาร/เครื่องดื่ม, ของใช้ทั่วไป, เสื้อผ้า, เครื่องใช้ไฟฟ้า, ยาสามัญ
2. ห้ามมโนชื่อสินค้า - ต้องใช้ข้อมูลจาก Tools เท่านั้น
3. ถ้าไม่มีข้อมูลจาก Tools ให้บอกว่าไม่พบสินค้า
4. ถ้าถามนอกเหนือ 5 หมวด ให้ปฏิเสธอย่างสุภาพ

เครื่องมือที่มี:
- semantic_search: ค้นหาสินค้าจากอาการหรือคำอธิบาย
- check_stock: ตรวจสอบสต็อก
- get_location: บอกตำแหน่งสินค้า
- add_to_shopping_list: เพิ่มสินค้าในรายการ
- summarize_route: สรุปเส้นทางและราคา
"""

def create_agent(config: Config):
    llm = ChatOpenAI(
        model="deepseek-chat",
        api_key=config.deepseek_api_key,
        base_url=config.deepseek_base_url,
        temperature=0.7
    )
    
    db = SupaBaseDB(config)
    embedder = EmbeddingService(config)
    
    shopping_list = []
    
    tools = [
        SemanticSearchTool(db=db, embedder=embedder),
        StockCheckerTool(db=db, embedder=embedder),
        NavigationTool(db=db),
        ShoppingListTool(db=db, shopping_list=shopping_list),
        RoutePlannerTool(db=db, shopping_list=shopping_list)
    ]
    
    prompt = ChatPromptTemplate.from_messages([
        ("system", SYSTEM_PROMPT),
        MessagesPlaceholder(variable_name="chat_history"),
        ("human", "{input}"),
        MessagesPlaceholder(variable_name="agent_scratchpad")
    ])
    
    memory = ConversationBufferMemory(memory_key="chat_history", return_messages=True)
    
    agent = create_openai_functions_agent(llm, tools, prompt)
    agent_executor = AgentExecutor(agent=agent, tools=tools, memory=memory, verbose=True)
    
    return agent_executor
