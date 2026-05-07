import os
from dotenv import load_dotenv
from pydantic import BaseModel

load_dotenv()

class Config(BaseModel):
    deepseek_api_key: str
    deepseek_base_url: str
    supabase_url: str
    supabase_key: str
    openai_api_key: str
    embedding_model: str
    use_local_embeddings: bool

def load_config() -> Config:
    return Config(
        deepseek_api_key=os.getenv("DEEPSEEK_API_KEY", ""),
        deepseek_base_url=os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com"),
        supabase_url=os.getenv("SUPABASE_URL", ""),
        supabase_key=os.getenv("SUPABASE_KEY", ""),
        openai_api_key=os.getenv("OPENAI_API_KEY", ""),
        embedding_model=os.getenv("EMBEDDING_MODEL", "intfloat/multilingual-e5-large"),
        use_local_embeddings=os.getenv("USE_LOCAL_EMBEDDINGS", "true").lower() == "true"
    )
