from sentence_transformers import SentenceTransformer
from typing import List
from config import Config

class EmbeddingService:
    def __init__(self, config: Config):
        self.config = config
        if config.use_local_embeddings:
            self.model = SentenceTransformer(config.embedding_model)
        else:
            self.model = None
    
    def embed_text(self, text: str) -> List[float]:
        if self.config.use_local_embeddings:
            return self.model.encode(text).tolist()
        else:
            from openai import OpenAI
            client = OpenAI(api_key=self.config.openai_api_key)
            response = client.embeddings.create(
                input=text,
                model="text-embedding-3-small"
            )
            return response.data[0].embedding
    
    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        if self.config.use_local_embeddings:
            return self.model.encode(texts).tolist()
        else:
            from openai import OpenAI
            client = OpenAI(api_key=self.config.openai_api_key)
            response = client.embeddings.create(
                input=texts,
                model="text-embedding-3-small"
            )
            return [item.embedding for item in response.data]
