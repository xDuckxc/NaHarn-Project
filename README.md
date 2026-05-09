# AIหน้าฮ่าน

Smart Mall Agentic Navigator สำหรับช่วยค้นหาสินค้าในห้าง เช็กสต็อก บอกตำแหน่งชั้นวาง เพิ่มสินค้าเข้าลิสต์ และสรุปเส้นทางเดินซื้อของผ่าน Chainlit UI

ผู้ช่วยในระบบชื่อ **น้องหลงทาง** พร้อม catchphrase: `หลงทางรึป่าว หาของไม่เจอใช่มั้ย`

## 1. วิธีติดตั้งและรันโปรเจกต์

### สิ่งที่ต้องมี

- Docker
- Docker Compose
- DeepSeek API key
- ไฟล์ `data/mall_products_500_with_3d.csv` อยู่ในโปรเจกต์

ไม่ต้องตั้งค่า Supabase เองในโหมดปกติ โปรเจกต์นี้จะรัน PostgreSQL + pgvector ผ่าน Docker ให้อัตโนมัติ

### ตั้งค่า `.env`

สร้างไฟล์ `.env` จากตัวอย่าง:

```bash
cp .env.example .env
```

จากนั้นเปิด `.env` แล้วใส่ค่าเดียวที่จำเป็น:

```env
DEEPSEEK_API_KEY=your_deepseek_api_key_here
```

ค่าอื่น ๆ ใช้ default ได้ เช่น:

```env
DEEPSEEK_MODEL=deepseek-v4-pro
PRODUCT_BACKEND=postgres
EMBEDDING_MODEL=intfloat/multilingual-e5-large
TOP_K_PRODUCTS=8
```

### รันด้วย Docker Compose

```bash
docker compose up --build
```

เปิดเว็บ:

```text
http://localhost:8000
```

ถ้าเพิ่งเปลี่ยน Dockerfile, dependencies, environment สำคัญ หรืออยากบังคับสร้าง container ใหม่ ให้ใช้:

```bash
docker compose up --build --force-recreate
```

ครั้งแรกจะใช้เวลานานกว่าปกติ เพราะระบบต้อง:

- ดาวน์โหลด embedding model `intfloat/multilingual-e5-large`
- สร้าง schema/table/index ของ pgvector
- อ่าน `data/mall_products_500_with_3d.csv`
- สร้าง embedding ให้สินค้า
- upsert ข้อมูลเข้า PostgreSQL

หลังจากโหลดครั้งแรกสำเร็จ รอบต่อไปจะเร็วขึ้น เพราะ Docker volume เก็บทั้ง DB และ HuggingFace cache ไว้แล้ว

### หยุดระบบ

```bash
docker compose down
```

### ล้าง DB และ cache เพื่อเริ่มใหม่ทั้งหมด

ใช้เมื่ออยากโหลดข้อมูลใหม่ตั้งแต่ศูนย์:

```bash
docker compose down -v
docker compose up --build --force-recreate
```

คำสั่ง `-v` จะลบ Docker volumes เช่น `pg-data` และ `hf-cache`

### เช็กสถานะและ log

```bash
docker compose ps -a
docker compose logs --tail=200 app-ui
docker compose logs --tail=200 db
```

เช็กจำนวนสินค้าใน DB:

```bash
docker compose exec -T db psql -U postgres -d postgres -c "select count(*) from products;"
```

ถ้า Docker แจ้ง `No such image: pgvector/pgvector:pg16` ให้ pull image ชัดเจนก่อน แล้วค่อยรัน Compose อีกครั้ง:

```bash
docker pull pgvector/pgvector:pg16
docker compose up --build
```

### คำเตือนที่เจอได้แต่ไม่ใช่ error

ข้อความเหล่านี้ไม่ใช่ปัญหาร้ายแรง:

```text
LangChainPendingDeprecationWarning
Translated markdown file for en-US not found. Defaulting to chainlit.md.
Warning: You are sending unauthenticated requests to the HF Hub.
adapter_config.json 404 Not Found
```

ความหมายโดยย่อ:

- LangChain warning: library แจ้งเรื่อง deprecation ในอนาคต
- Chainlit translation warning: ไม่มีไฟล์แปลภาษาแยก จึงใช้ `chainlit.md`
- HF Hub warning: ไม่ได้ใส่ HuggingFace token จึงโหลดแบบ unauthenticated
- `adapter_config.json 404`: Transformers เช็ก optional adapter file ที่ model นี้ไม่มี

## 2. โครงสร้างโปรเจกต์

```text
.
├── src/
│   └── naharn/
│       ├── app.py            # Chainlit entry point และ callback สำหรับ DeepSeek reasoning
│       ├── agents.py         # LangGraph workflow และ logic ค้นหา/ตะกร้า/ตอบกลับ
│       ├── graph_state.py    # TypedDict state, product schema helper, cart/route utilities
│       ├── product_store.py  # Database access layer สำหรับ PostgreSQL/Supabase
│       ├── db_loader.py      # สร้าง schema, สร้าง embedding, load CSV เข้า DB
│       ├── agent_logger.py   # เขียน operational trace สำหรับหน้า Agent Logs
│       └── paths.py          # path กลางของ project/data/public/logs
├── data/
│   └── mall_products_500_with_3d.csv
│                             # ข้อมูลสินค้าจริงพร้อมพิกัด 3D ที่ใช้โหลดเข้า DB
├── public/
│   ├── model_viewer.html     # 3D Navigator
│   ├── agent_logs.html       # หน้าอ่าน operational trace
│   ├── Naharn_3D.glb         # โมเดล 3D
│   └── three/                # Three.js modules ที่ viewer import จริง
├── chainlit.md               # Welcome/usage page ที่แสดงใน Chainlit
├── requirements.txt          # Python dependencies
├── Dockerfile                # Image สำหรับ Chainlit app
├── docker-compose.yml        # app-ui, db, hf-cache-init และ volumes
├── scripts/
│   └── start.sh              # startup script: init DB/load data แล้วเปิด Chainlit
├── .env.example              # template env vars
├── .env                      # env จริงบนเครื่อง local ไม่ควร commit
├── .gitignore                # ignore secret/cache/runtime artifacts
└── .dockerignore             # ลดไฟล์ไม่จำเป็นใน Docker build context
```

### Flow ตอนระบบเริ่ม

1. `docker-compose.yml` เปิด `db` ด้วย image `pgvector/pgvector:pg16`
2. `hf-cache-init` แก้ permission ของ HuggingFace cache volume
3. `app-ui` รัน `scripts/start.sh`
4. `start.sh` ตรวจ `DEEPSEEK_API_KEY`
5. `python -m naharn.db_loader --init-db --skip-if-loaded` สร้าง schema และโหลด CSV ถ้ายังไม่มีข้อมูล
6. `chainlit run src/naharn/app.py` เปิด UI ที่ port `8000`

## 3. เครื่องมือและไลบรารีที่ใช้

| เครื่องมือ/ไลบรารี | หน้าที่ |
|---|---|
| Docker | สร้าง runtime ที่ reproducible ไม่ต้องลง Python/Postgres เองบนเครื่อง |
| Docker Compose | รันหลาย service พร้อมกัน ได้แก่ `app-ui`, `db`, `hf-cache-init` |
| Chainlit | สร้าง chat UI ที่ browser และจัดการ session/chat event |
| LangGraph | สร้าง multi-agent graph สำหรับ supervisor, search, navigation, cart/route planner |
| LangChain Core | ใช้ message objects, callbacks, tools และ interface กลางของ agent workflow |
| LangChain Classic | ใช้ `ConversationBufferMemory` สำหรับ compatibility กับ memory แบบเดิม |
| DeepSeek API | LLM หลักของระบบ ใช้ผ่าน OpenAI-compatible client และอ่าน `reasoning_content` |
| OpenAI Python SDK | client สำหรับเรียก DeepSeek endpoint แบบ OpenAI-compatible API |
| SentenceTransformers | โหลดและรัน embedding model |
| `intfloat/multilingual-e5-large` | embedding model ภาษาไทย/หลายภาษา ขนาด vector 1024 dimensions |
| PostgreSQL | database หลักสำหรับเก็บสินค้า |
| pgvector | extension สำหรับเก็บและค้นหา vector similarity |
| psycopg | Python driver สำหรับเชื่อม PostgreSQL local |
| Supabase Python | รองรับ optional Supabase backend หากอยากเปลี่ยนไปใช้ Supabase cloud ภายหลัง |
| python-dotenv | โหลดค่าจาก `.env` ตอนรัน local/scripts |
| NumPy | dependency พื้นฐานสำหรับงาน vector/model ecosystem |

## 4. Architecture ของ Agent

ระบบใช้ LangGraph state ที่มีข้อมูลหลัก:

- `messages`: ประวัติ message ใน conversation
- `shopping_list`: list ของ product IDs ที่ user เพิ่มเข้าตะกร้า
- `current_context`: context ล่าสุดของ graph
- `agent_plan`: JSON plan จาก LLM planner เช่น route, tools, show_map, confidence
- `search_results`: ผลค้นหาจาก vector DB
- `validated_results`: ผลที่ผ่านการเช็ก stock และ format location แล้ว
- `constraints`: filter เช่น category, price, จำนวนรายการ, group by brand

Node หลัก:

| Node | หน้าที่ |
|---|---|
| Supervisor Agent | ใช้ LLM planner เลือก route และ tool เช่น `search_products`, `add_to_cart`, `show_map`, `summarize_route` โดยมี deterministic fallback |
| Search & Filter Node | extract constraint, embed query, ค้นหา pgvector, apply metadata filters |
| Navigation & Stock Evaluator Node | ตัดสินค้าที่ stock หมด, format location เป็นภาษาไทย, จำกัดจำนวนผลลัพธ์ |
| Cart & Route Planner Node | ใช้ tool `add_to_cart` เพิ่มสินค้าเข้าลิสต์, สรุป route, คำนวณราคา และส่ง pin ของลิสต์ไป 3D Viewer |
| Show Map Node | ใช้ tool `show_map` เพื่อเตรียม pin จากผลค้นหาล่าสุดหรือ shopping list แล้วเปิด `/public/model_viewer.html` |
| General Node | ตอบคำถามทั่วไปใน persona น้องหลงทาง |

## 5. ตัวอย่างการใช้งานในหน้าเว็บ

ค้นหาพร้อมงบ:

```text
หาแชมพูไม่เกิน 200
```

ขอจำนวนแบรนด์:

```text
อยากได้ขนมมันฝรั่งทอด แนะนำ 3 แบรนด์
```

ขอตำแหน่งสินค้า:

```text
มียาแก้ปวดอยู่ตรงไหน
```

เพิ่มของเข้าลิสต์:

```text
เพิ่ม 12
```

เพิ่มหลายชิ้น:

```text
เพิ่ม 12 34 56
```

เพิ่มแล้วเปิดแผนที่:

```text
เพิ่ม 12 แล้วแสดงแผนที่
```

แสดงแผนที่จากผลค้นหาหรือลิสต์ล่าสุด:

```text
แสดงแผนที่
```

สรุปเส้นทางเดินซื้อของ:

```text
สรุปเส้นทาง
```

## 6. Environment variables สำคัญ

| ตัวแปร | จำเป็นไหม | ค่า default | หน้าที่ |
|---|---:|---|---|
| `DEEPSEEK_API_KEY` | จำเป็น | ไม่มี | API key สำหรับเรียก DeepSeek |
| `DEEPSEEK_BASE_URL` | ไม่จำเป็น | `https://api.deepseek.com` | endpoint ของ DeepSeek |
| `DEEPSEEK_MODEL` | ไม่จำเป็น | `deepseek-v4-pro` | ชื่อ model ที่ใช้ |
| `DEEPSEEK_REASONING_EFFORT` | ไม่จำเป็น | `high` | ระดับ reasoning effort |
| `DEEPSEEK_MAX_TOKENS` | ไม่จำเป็น | `2048` | token สูงสุดต่อ response |
| `USE_LLM_PLANNER` | ไม่จำเป็น | `true` | เปิด LLM planner ให้เลือก route/tool ก่อน execute |
| `USE_LLM_CONSTRAINTS` | ไม่จำเป็น | `true` | เปิด LLM extraction สำหรับ filter สินค้า |
| `USE_LLM_GENERAL` | ไม่จำเป็น | `true` | เปิด LLM responder สำหรับคำถามทั่วไปที่ยังเกี่ยวกับการซื้อของ/สินค้าในห้าง |
| `PRODUCT_BACKEND` | ไม่จำเป็น | `postgres` | backend สินค้า ปกติใช้ local Postgres |
| `PRODUCT_CSV` | ไม่จำเป็น | `data/mall_products_500_with_3d.csv` | path CSV ที่ใช้โหลดสินค้าเข้า DB |
| `PRODUCT_DATABASE_URL` | ไม่จำเป็นใน Docker | compose ตั้งให้เอง | connection string ของ product DB |
| `APP_AUTO_LOAD_DB` | ไม่จำเป็น | `true` | auto init/load DB ตอน app start |
| `EMBEDDING_MODEL` | ไม่จำเป็น | `intfloat/multilingual-e5-large` | embedding model |
| `PRODUCT_TABLE` | ไม่จำเป็น | `products` | table ที่เก็บสินค้า |
| `TOP_K_PRODUCTS` | ไม่จำเป็น | `8` | จำนวนผลค้นหาเบื้องต้น |

## 7. หมายเหตุเรื่องข้อมูล

โปรเจกต์ไม่สร้าง mock data เอง ระบบจะใช้ข้อมูลจาก `data/mall_products_500_with_3d.csv` (มี coordinates_3d) เท่านั้น

ถ้าเปลี่ยน CSV แล้วอยาก reload DB ใหม่ ให้รัน:

```bash
docker compose down -v
docker compose up --build --force-recreate
```

## 8. 3D Digital Twin Navigator

ระบบมี 3D mall navigator ที่แสดงตำแหน่งสินค้าแบบ 3 มิติ:

- **โมเดล**: `public/Naharn_3D.glb` (simple floor model 100m × 50m)
- **พิกัด**: แต่ละสินค้ามี `coordinates_3d` (x, y, z) คำนวณจาก `location_info`
- **Zones**: A (0-20m), B (20-40m), C (40-60m), D (60-80m), E (80-100m)
- **Viewer**: เข้าถึงได้ที่ `/public/model_viewer.html` ใน Chainlit UI

### การใช้งาน 3D Viewer

1. เปิด Chainlit UI ที่ `http://localhost:8000`
2. คลิกลิงก์ **"เปิด 3D Navigator"** ในข้อความต้อนรับ
3. ใช้เมาส์ลากเพื่อหมุนมุมมอง, scroll เพื่อ zoom
4. Pin สีแดงแสดงตำแหน่งสินค้า (เมื่อค้นหา)

### API สำหรับ JavaScript Bridge

```javascript
// เพิ่ม pin สินค้า
window.mall3D.addPin(id, x, y, z, name);

// ลบ pin ทั้งหมด
window.mall3D.clearPins();

// Zoom กล้องไปยังตำแหน่ง
window.mall3D.focusOn(x, y, z, duration);
```

Runtime output เช่น `public/pins.json`, `public/agent_logs.json` และ `logs/` จะถูกสร้างใหม่อัตโนมัติระหว่างใช้งาน จึงไม่ได้เก็บไว้ในโครงสร้างโปรเจกต์หลัก
