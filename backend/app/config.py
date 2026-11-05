import os


OLLAMA_URL = os.getenv("OLLAMA_URL", "http://ollama:11434/api/generate")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.2:3b")
INSIGHT_USE_LLM = os.getenv("INSIGHT_USE_LLM", "true").lower() == "true"
INSIGHT_LLM_TIMEOUT = float(os.getenv("INSIGHT_LLM_TIMEOUT", "90"))
ENABLE_LLM_GRAMMAR = os.getenv("ENABLE_LLM_GRAMMAR", "false").lower() == "true"
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID", "")
JWT_SECRET = os.getenv("JWT_SECRET", "local-development-only-change-me")
JWT_EXPIRE_HOURS = int(os.getenv("JWT_EXPIRE_HOURS", "24"))
