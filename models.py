from pydantic import BaseModel
from typing import List, Optional

class Req(BaseModel):
    documents: str
    questions: List[str]
    ocr_method: Optional[str] = "auto"  # NEW: OCR method selection

class ImageReq(BaseModel):
    """NEW: Request model for direct image upload"""
    questions: List[str]
    ocr_method: Optional[str] = "auto"

class Resp(BaseModel):
    answers: List[str]
    processing_info: Optional[dict] = None  # NEW: Processing metadata