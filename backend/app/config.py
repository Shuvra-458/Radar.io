import os
from dotenv import load_dotenv

load_dotenv()

import os
from dotenv import load_dotenv

load_dotenv()

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
TAVILY_API_KEY = os.getenv("TAVILY_API_KEY")

LLM_MODEL = "openai/gpt-oss-120b"
LLM_TEMPERATURE = 0.0   
EMBED_MODEL = "models/gemini-embedding-001"   # 768-dimesions
EMBED_DIM = 768

LLM_MAX_RETRIES = 3
LLM_TIMEOUT_S = 30

DATABASE_URL = os.getenv("DATABASE_URL")