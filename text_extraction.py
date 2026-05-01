import re
import asyncio
import requests
import fitz  # PyMuPDF
from bs4 import BeautifulSoup
from concurrent.futures import ThreadPoolExecutor
from typing import List
from config import OVERLAP_WORDS, DEFAULT_DESIRED_CHUNK_WORD_LEN, DEFAULT_MIN_CHUNK_WORD_LEN
from sklearn.cluster import AgglomerativeClustering

# NEW IMPORTS FOR IMAGE PROCESSING
from PIL import Image
import cv2
import numpy as np
from pathlib import Path
import io
import base64

# OCR library imports
try:
    import easyocr
    EASYOCR_AVAILABLE = True
except ImportError:
    EASYOCR_AVAILABLE = False

try:
    import pytesseract
    TESSERACT_AVAILABLE = True
except ImportError:
    TESSERACT_AVAILABLE = False

try:
    import google.generativeai as genai
    from config import GEMINI_API_KEY
    GEMINI_AVAILABLE = bool(GEMINI_API_KEY)
except ImportError:
    GEMINI_AVAILABLE = False

executor = ThreadPoolExecutor(max_workers=16)

# EXISTING FUNCTIONS (unchanged)
def contains_url(text: str) -> bool:
    return bool(re.search(r'https?://\S+', text))

def is_pdf_url(url: str) -> bool:
    url_lower = url.lower()
    return url_lower.endswith(".pdf") or "pdf" in url_lower.split("?")[0].split(".")[-1]

# NEW FUNCTION FOR IMAGE DETECTION
def is_image_url(url: str) -> bool:
    """Check if URL points to an image file"""
    url_lower = url.lower()
    image_extensions = ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.webp']
    return any(url_lower.endswith(ext) for ext in image_extensions)

# NEW FUNCTION FOR IMAGE PREPROCESSING
def preprocess_image_for_ocr(image: np.ndarray) -> np.ndarray:
    """Preprocess image to improve OCR accuracy"""
    # Convert to grayscale if needed
    if len(image.shape) == 3:
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    else:
        gray = image

    # Noise removal
    denoised = cv2.medianBlur(gray, 3)

    # Thresholding
    _, thresh = cv2.threshold(denoised, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

    return thresh

# NEW OCR FUNCTIONS
async def extract_text_with_easyocr(image_data: bytes) -> str:
    """Extract text using EasyOCR"""
    if not EASYOCR_AVAILABLE:
        raise ImportError("EasyOCR not installed")

    def _extract():
        reader = easyocr.Reader(['en'])  # Add more languages as needed
        nparr = np.frombuffer(image_data, np.uint8)
        image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        processed_image = preprocess_image_for_ocr(image)
        results = reader.readtext(processed_image)
        text_parts = [result[1] for result in results]
        return ' '.join(text_parts)

    return await asyncio.get_event_loop().run_in_executor(executor, _extract)

async def extract_text_with_tesseract(image_data: bytes) -> str:
    """Extract text using Tesseract OCR"""
    if not TESSERACT_AVAILABLE:
        raise ImportError("Tesseract not installed")

    def _extract():
        image = Image.open(io.BytesIO(image_data))
        image_array = np.array(image)
        processed_image = preprocess_image_for_ocr(image_array)
        pil_image = Image.fromarray(processed_image)
        text = pytesseract.image_to_string(pil_image, config='--oem 3 --psm 6')
        return text.strip()

    return await asyncio.get_event_loop().run_in_executor(executor, _extract)

async def extract_text_with_gemini(image_data: bytes) -> str:
    """Extract text using Google Gemini Vision"""
    if not GEMINI_AVAILABLE:
        raise ImportError("Gemini Vision not available")

    def _extract():
        genai.configure(api_key=GEMINI_API_KEY)
        model = genai.GenerativeModel("gemini-1.5-flash")
        image_b64 = base64.b64encode(image_data).decode()

        prompt = """Extract all text from this image. Return only the text content without any formatting or explanations."""

        response = model.generate_content([
            prompt,
            {"mime_type": "image/jpeg", "data": image_b64}
        ])

        return response.text.strip() if response.text else ""

    return await asyncio.get_event_loop().run_in_executor(executor, _extract)

async def extract_text_from_image(image_data: bytes, ocr_method: str = "auto") -> str:
    """Extract text from image using specified OCR method"""
    if ocr_method == "auto":
        # Try methods in order of preference
        for method in ['gemini', 'easyocr', 'tesseract']:
            try:
                if method == 'gemini' and GEMINI_AVAILABLE:
                    return await extract_text_with_gemini(image_data)
                elif method == 'easyocr' and EASYOCR_AVAILABLE:
                    return await extract_text_with_easyocr(image_data)
                elif method == 'tesseract' and TESSERACT_AVAILABLE:
                    return await extract_text_with_tesseract(image_data)
            except Exception as e:
                print(f"Failed to extract text with {method}: {e}")
                continue

        raise RuntimeError("No OCR method available")

    # Use specific method
    if ocr_method == "gemini":
        return await extract_text_with_gemini(image_data)
    elif ocr_method == "easyocr":
        return await extract_text_with_easyocr(image_data)
    elif ocr_method == "tesseract":
        return await extract_text_with_tesseract(image_data)
    else:
        raise ValueError(f"Unknown OCR method: {ocr_method}")

async def extract_text_from_file(file_content: bytes, filename: str, ocr_method: str = "auto") -> str:
    """Extract text from uploaded file (supports PDFs and images)"""
    file_ext = Path(filename).suffix.lower()

    if file_ext in ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.webp']:
        # Handle image files
        return await extract_text_from_image(file_content, ocr_method)
    elif file_ext == '.pdf':
        # Handle PDF files (use existing logic)
        def extract_pdf_inner():
            with fitz.open(stream=file_content, filetype="pdf") as doc:
                return " ".join(page.get_text() for page in doc if page.get_text().strip())

        text = await asyncio.get_event_loop().run_in_executor(executor, extract_pdf_inner)
        return re.sub(r'\s+', ' ', text).strip()
    else:
        raise ValueError(f"Unsupported file type: {file_ext}")

session = requests.Session()

# ENHANCED EXTRACT_TEXT FUNCTION (replaces your existing one)
async def extract_text(url: str, ocr_method: str = "auto") -> str:
    """
    Extract text from URL (PDF, webpage, or image) - ENHANCED VERSION
    """
    # NEW: Check if it's an image URL
    if is_image_url(url):
        # Handle image URLs
        def download_image():
            r = session.get(url, timeout=30)
            r.raise_for_status()
            return r.content

        image_data = await asyncio.get_event_loop().run_in_executor(executor, download_image)
        text = await extract_text_from_image(image_data, ocr_method)
        return re.sub(r'\s+', ' ', text).strip()

    # EXISTING: Handle PDFs
    elif is_pdf_url(url):
        def extract_pdf_inner():
            r = session.get(url, timeout=30)
            r.raise_for_status()
            with fitz.open(stream=r.content, filetype="pdf") as doc:
                return " ".join(page.get_text() for page in doc if page.get_text().strip())

        text = await asyncio.get_event_loop().run_in_executor(executor, extract_pdf_inner)
    else:
        # EXISTING: Handle webpages
        def extract_webpage_inner():
            r = session.get(url, timeout=30)
            r.raise_for_status()
            soup = BeautifulSoup(r.text, "html.parser")
            for tag in soup(["script", "style"]):
                tag.decompose()
            return soup.get_text(separator=' ')

        text = await asyncio.get_event_loop().run_in_executor(executor, extract_webpage_inner)

    return re.sub(r'\s+', ' ', text).strip()

# EXISTING FUNCTIONS (unchanged)
def split_into_paragraphs(text: str) -> List[str]:
    paragraphs = [p.strip() for p in re.split(r'\n\s*\n', text) if p.strip()]
    return paragraphs

def split_into_sentences(text: str) -> List[str]:
    sentences = re.split(r'(?<=[.!?])\s+', text)
    return [s.strip() for s in sentences if s.strip()]

def add_overlap_between_chunks(chunks: List[str], overlap_word_count: int = OVERLAP_WORDS) -> List[str]:
    overlapped_chunks = []
    prev_words = []

    for chunk in chunks:
        current_words = chunk.split()
        if prev_words:
            combined_words = prev_words[-overlap_word_count:] + current_words
        else:
            combined_words = current_words
        overlapped_chunks.append(" ".join(combined_words))
        prev_words = current_words

    return overlapped_chunks

def smarter_chunking(text: str,
                     desired_chunk_word_len: int = DEFAULT_DESIRED_CHUNK_WORD_LEN,
                     min_chunk_word_len: int = DEFAULT_MIN_CHUNK_WORD_LEN,
                     embedding_model=None) -> List[str]:
    paragraphs = split_into_paragraphs(text)

    if not paragraphs or all(len(p.split()) < min_chunk_word_len for p in paragraphs):
        paragraphs = split_into_sentences(text)

    embeddings = embedding_model.encode(paragraphs, convert_to_numpy=True)

    total_words = sum(len(p.split()) for p in paragraphs)
    n_clusters = max(1, total_words // desired_chunk_word_len)
    n_clusters = min(n_clusters, len(paragraphs))

    if n_clusters == 1:
        chunks = [" ".join(paragraphs)]
    else:
        clusterer = AgglomerativeClustering(n_clusters=n_clusters)
        cluster_ids = clusterer.fit_predict(embeddings)

        clusters = {}
        for i, cid in enumerate(cluster_ids):
            clusters.setdefault(cid, []).append(paragraphs[i])

        chunks = [" ".join(clusters[cid]).strip() for cid in sorted(clusters.keys())]

    chunks = add_overlap_between_chunks(chunks, overlap_word_count=OVERLAP_WORDS)
    return chunks