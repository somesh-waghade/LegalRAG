"""
pdf_reader.py – Extract text from PDF files using pypdf.

Returns structured page-level data including page number, text content,
and source filename for metadata storage in the vector database.
"""

import os
from typing import List, Dict, Any
from pypdf import PdfReader


def extract_text_from_pdf(file_path: str) -> List[Dict[str, Any]]:
    """
    Extract text from each page of a PDF file.

    Args:
        file_path: Absolute path to the PDF file.

    Returns:
        List of dicts with keys: page_num, text, source_filename
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"PDF file not found: {file_path}")

    filename = os.path.basename(file_path)
    pages = []

    reader = PdfReader(file_path)
    for page_index, page in enumerate(reader.pages):
        text = page.extract_text()
        if not text:
            text = ""

        # Skip empty or near-empty pages
        if len(text.strip()) < 10:
            continue

        pages.append({
            "page_num": page_index + 1,   # 1-indexed
            "text": text.strip(),
            "source_filename": filename,
        })

    return pages


def chunk_pages(
    pages: List[Dict[str, Any]],
    chunk_size: int = 512,
    chunk_overlap: int = 50,
) -> List[Dict[str, Any]]:
    """
    Split page text into overlapping chunks for better retrieval.

    Args:
        pages: Output of extract_text_from_pdf().
        chunk_size: Maximum characters per chunk.
        chunk_overlap: Number of overlapping characters between consecutive chunks.

    Returns:
        List of chunk dicts with keys: chunk_id, text, page_num, source_filename
    """
    chunks = []
    chunk_id = 0

    for page in pages:
        text = page["text"]
        page_num = page["page_num"]
        source_filename = page["source_filename"]

        start = 0
        while start < len(text):
            end = start + chunk_size
            chunk_text = text[start:end].strip()

            if len(chunk_text) > 20:  # Skip trivially small chunks
                chunks.append({
                    "chunk_id": chunk_id,
                    "text": chunk_text,
                    "page_num": page_num,
                    "source_filename": source_filename,
                })
                chunk_id += 1

            if end >= len(text):
                break
            start = end - chunk_overlap

    return chunks


def process_pdf(file_path: str) -> List[Dict[str, Any]]:
    """
    Full pipeline: extract text from PDF and split into chunks.

    Args:
        file_path: Path to the PDF file.

    Returns:
        List of chunk dicts ready for embedding and storage.
    """
    pages = extract_text_from_pdf(file_path)
    chunks = chunk_pages(pages)
    return chunks
