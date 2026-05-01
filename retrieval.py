import re
import numpy as np
import faiss
import asyncio
from typing import List, Tuple
from rank_bm25 import BM25Okapi
import logging

from embedding import embed_batch  # use your embedding.py
from config import (
    BM25_TOP_K,
    DEFAULT_PASS1_K,
    DEFAULT_PASS2_K,
    SIMILARITY_THRESHOLD,
    DEFAULT_QUERY_VARIANTS,
)

logger = logging.getLogger("hackrx")

def build_bm25_index(chunks: List[str]) -> BM25Okapi:
    """Build BM25 index from tokenized chunks."""
    tokenized_chunks = [re.findall(r"\w+", c.lower()) for c in chunks]
    bm25 = BM25Okapi(tokenized_chunks)
    return bm25

def bm25_retrieve(bm25: BM25Okapi, question: str, top_n: int = BM25_TOP_K) -> List[int]:
    tokenized_query = re.findall(r"\w+", question.lower())
    scores = bm25.get_scores(tokenized_query)
    top_indices = np.argsort(scores)[::-1][:top_n]
    return top_indices.tolist()

def build_faiss_index(embeddings: List[List[float]]) -> faiss.IndexFlatIP:
    """Normalize and create a FAISS inner product index."""
    matrix = np.array(embeddings, dtype=np.float32)
    faiss.normalize_L2(matrix)
    index = faiss.IndexFlatIP(matrix.shape[1])
    index.add(matrix)
    return index

def soft_keyword_boost(query: str, candidates: List[Tuple[float, str]]) -> List[Tuple[float, str]]:
    """Boost similarity score by keyword overlap between query and chunk."""
    kw = set(re.findall(r"\w+", query.lower()))
    boosted = []
    for sim, chunk in candidates:
        overlap = len(kw.intersection(re.findall(r"\w+", chunk.lower())))
        boosted.append((sim * (1.0 + 0.1 * overlap), chunk))
    boosted.sort(key=lambda x: x[0], reverse=True)
    return boosted

async def expand_question(question: str, max_variants: int = DEFAULT_QUERY_VARIANTS) -> List[str]:
    """
    Lightweight query expansion without an extra LLM call.
    Keeps retrieval fast and avoids dependency on a second generation request.
    """
    max_variants = max(1, int(max_variants))
    normalized = re.sub(r"\s+", " ", question).strip()

    variants = [
        normalized,
        f"Provide details about: {normalized}",
        f"What does this document say about: {normalized}",
        f"Find policy clauses for: {normalized}",
    ]

    # Preserve order and uniqueness.
    deduped = []
    seen = set()
    for q in variants:
        key = q.lower()
        if key not in seen:
            seen.add(key)
            deduped.append(q)
        if len(deduped) >= max_variants:
            break
    return deduped

async def dual_pass_retrieve(
    question: str,
    chunks: List[str],
    faiss_index,
    bm25: BM25Okapi,
    pass1_k: int = DEFAULT_PASS1_K,
    pass2_k: int = DEFAULT_PASS2_K,
    max_variants: int = DEFAULT_QUERY_VARIANTS,
) -> List[str]:
    """
    First pass: BM25 retrieval of candidate chunks.
    Second pass: FAISS similarity search on BM25 candidates embedding.
    """

    # Ensure numeric parameters are integers to avoid comparison errors
    pass1_k = int(pass1_k)
    pass2_k = int(pass2_k)
    max_variants = int(max_variants)

    logger.info(f"dual_pass_retrieve parameters: pass1_k={pass1_k} ({type(pass1_k)}), pass2_k={pass2_k} ({type(pass2_k)}), max_variants={max_variants} ({type(max_variants)})")

    bm25_indices = bm25_retrieve(bm25, question, top_n=BM25_TOP_K)

    candidate_chunks = [chunks[i] for i in bm25_indices]

    candidate_embeddings = await embed_batch(candidate_chunks, concurrency_limit=20)

    faiss_candidate_index = build_faiss_index(candidate_embeddings)

    variants = await expand_question(question, max_variants)

    all_scores = []

    for variant in variants:
        q_emb = (await embed_batch([variant], concurrency_limit=20))[0]
        vec = np.array([q_emb], dtype=np.float32)
        faiss.normalize_L2(vec)
        k = min(pass1_k, len(candidate_chunks))
        if k == 0:
            continue
        D, I = faiss_candidate_index.search(vec, k)
        for dist, idx in zip(D[0], I[0]):
            if dist > SIMILARITY_THRESHOLD:
                try:
                    idx_int = int(idx)
                    if 0 <= idx_int < len(candidate_chunks):
                        all_scores.append((float(dist), candidate_chunks[idx_int]))
                except Exception as e:
                    logger.warning(f"Invalid FAISS candidate index {idx} or error: {e}")

    boosted = soft_keyword_boost(question, all_scores)

    seen = set()
    results = []

    for _, chunk in boosted:
        if chunk not in seen:
            seen.add(chunk)
            results.append(chunk)
        # This line caused your error if pass2_k was a str
        if len(results) >= pass2_k:
            break

    return results
