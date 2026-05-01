
from dotenv import load_dotenv
load_dotenv()  # Load variables from .env
import os
DEFAULT_PASS1_K = int(os.getenv("DEFAULT_PASS1_K", "100"))
DEFAULT_PASS2_K = int(os.getenv("DEFAULT_PASS2_K", "50"))
BM25_TOP_K = int(os.getenv("BM25_TOP_K", "50"))
DEFAULT_QUERY_VARIANTS = int(os.getenv("DEFAULT_QUERY_VARIANTS", "5"))
# ... (similarly for other numeric params)


GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.1-8b-instant")

MAX_WORKERS = min(64, (os.cpu_count() or 4) * 4)

# Chunking parameters
DEFAULT_DESIRED_CHUNK_WORD_LEN = 150
DEFAULT_MIN_CHUNK_WORD_LEN = 80
OVERLAP_WORDS = 30

# BM25 retrieval top-k
BM25_TOP_K = 50

# FAISS retrieval top-K limits
DEFAULT_PASS1_K = 100
DEFAULT_PASS2_K = 50
SIMILARITY_THRESHOLD = 0.05

# Token limits and concurrency
MAX_OUTPUT_TOKENS = 400
DEFAULT_CONCURRENCY_LIMIT = 16

# Query expansion
DEFAULT_QUERY_VARIANTS = 5
