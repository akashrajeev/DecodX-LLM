import logging
import asyncio
import time
from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from typing import List

from models import Req, Resp
from text_extraction import extract_text, smarter_chunking, extract_text_from_file
from retrieval import build_bm25_index, dual_pass_retrieve
from answer_generation import generate_answer
from embedding import embedding_model
from config import DEFAULT_CONCURRENCY_LIMIT
from dotenv import load_dotenv
load_dotenv()  # <-- This will load variables from .env into os.environ

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("hackrx")

app = FastAPI(title="HackRx Enhanced LLM API", version="v3", description="Now with image processing capabilities!")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# EXISTING FUNCTION - Enhanced with OCR support
async def process(doc_url: str, questions: list[str], ocr_method: str = "auto") -> tuple:
    answers = []
    processing_info = {"ocr_method_used": ocr_method}
    start_time = time.time()

    if questions:
        try:
            text = await extract_text(doc_url, ocr_method)
            chunks = smarter_chunking(text, embedding_model=embedding_model)

            if not chunks:
                answers.extend(["Information not found in the policy."] * len(questions))
                return answers, processing_info

            bm25 = build_bm25_index(chunks)
            processing_info["total_chunks"] = len(chunks)

            sem = asyncio.Semaphore(DEFAULT_CONCURRENCY_LIMIT)

            async def answer_question(q: str) -> str:
                async with sem:
                    ctx_chunks = await dual_pass_retrieve(q, chunks, faiss_index=None, bm25=bm25)
                    if not ctx_chunks:
                        return "Information not found in the policy."
                    return await generate_answer(q, ctx_chunks)

            answers.extend(await asyncio.gather(*[answer_question(q) for q in questions]))

        except Exception as e:
            logger.error(f"Document QA error: {e}")
            answers.extend([f"Error processing question: {e}"] * len(questions))

    processing_info["processing_time_seconds"] = round(time.time() - start_time, 2)
    return answers, processing_info

# NEW: Function to process uploaded files
async def process_uploaded_files(files: List[UploadFile], questions: List[str], ocr_method: str = "auto") -> tuple:
    answers = []
    processing_info = {"files_processed": len(files), "ocr_method_used": ocr_method}
    start_time = time.time()

    if questions and files:
        try:
            all_chunks = []

            for file in files:
                try:
                    content = await file.read()
                    text = await extract_text_from_file(content, file.filename, ocr_method)

                    if text.strip():
                        chunks = smarter_chunking(text, embedding_model=embedding_model)
                        all_chunks.extend(chunks)
                        logger.info(f"Processed file: {file.filename}, extracted {len(chunks)} chunks")
                except Exception as e:
                    logger.error(f"Error processing file {file.filename}: {e}")
                    continue

            processing_info["total_chunks"] = len(all_chunks)

            if not all_chunks:
                answers.extend(["No content could be extracted from the uploaded files."] * len(questions))
                return answers, processing_info

            # Build search indexes
            bm25 = build_bm25_index(all_chunks)

            # Process questions
            sem = asyncio.Semaphore(DEFAULT_CONCURRENCY_LIMIT)

            async def answer_question(q: str) -> str:
                async with sem:
                    ctx_chunks = await dual_pass_retrieve(q, all_chunks, faiss_index=None, bm25=bm25)
                    if not ctx_chunks:
                        return "Information not found in the uploaded files."
                    return await generate_answer(q, ctx_chunks)

            answers.extend(await asyncio.gather(*[answer_question(q) for q in questions]))

        except Exception as e:
            logger.error(f"File processing error: {e}")
            answers.extend([f"Error processing files: {e}"] * len(questions))

    processing_info["processing_time_seconds"] = round(time.time() - start_time, 2)
    return answers, processing_info

# EXISTING ENDPOINT - Enhanced with OCR support
@app.post("/hackrx/run", response_model=Resp)
async def run(req: Req):
    try:
        answers, processing_info = await process(req.documents, req.questions, req.ocr_method)
        return Resp(answers=answers, processing_info=processing_info)
    except Exception as e:
        logger.exception(f"Internal error: {e}")
        raise HTTPException(500, f"Internal server error: {e}")

# NEW ENDPOINT: File upload support
@app.post("/hackrx/upload-images", response_model=Resp)
async def upload_images(
    files: List[UploadFile] = File(...),
    questions: List[str] = Form(...),
    ocr_method: str = Form("auto")
):
    """NEW: Upload image files directly"""
    try:
        # Validate file types
        allowed_extensions = {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.webp', '.pdf'}
        for file in files:
            file_ext = file.filename.lower().split('.')[-1] if '.' in file.filename else ''
            if f'.{file_ext}' not in allowed_extensions:
                raise HTTPException(400, f"Unsupported file type: {file.filename}")

        answers, processing_info = await process_uploaded_files(files, questions, ocr_method)
        return Resp(answers=answers, processing_info=processing_info)
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Internal error: {e}")
        raise HTTPException(500, f"Internal server error: {e}")

# EXISTING ENDPOINT - Enhanced health check
@app.get("/health")
async def health():
    # Check available OCR methods
    supported_ocr = []

    try:
        import easyocr
        supported_ocr.append("easyocr")
    except ImportError:
        pass

    try:
        import pytesseract
        supported_ocr.append("tesseract")
    except ImportError:
        pass

    try:
        import google.generativeai as genai
        from config import GEMINI_API_KEY
        if GEMINI_API_KEY:
            supported_ocr.append("gemini")
    except ImportError:
        pass

    return {
        "status": "ok", 
        "multilingual": True, 
        "dynamic_context": True,
        "image_processing": len(supported_ocr) > 0,
        "supported_ocr_methods": supported_ocr
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, workers=1)