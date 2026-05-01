# HackRx LLM Project

## Overview
This project is a modular LLM-powered service to answer questions based on documents.

## Structure
- `app.py`: FastAPI app entrypoint
- `config.py`: Configuration and environment values
- `models.py`: Request and response schema models
- `text_extraction.py`: Document text extraction & chunking
- `retrieval.py`: BM25 and FAISS retrieval logic
- `embedding.py`: Embedding model handling
- `answer_generation.py`: LLM answer generation
- `utils.py`: Helper functions
- `tests/`: Unit and integration tests

## Setup
Install dependencies from `requirements.txt` and set environment variables for your API keys.

Create a `.env` file with:

```
GROQ_API_KEY=your_groq_api_key
GROQ_MODEL=llama-3.1-8b-instant
GEMINI_API_KEY=optional_for_gemini_ocr
```

## Usage
Run the app with:
uvicorn app:app --host 0.0.0.0 --port 8000 --workers 1

Run Streamlit frontend:
streamlit run streamlit_app.py

