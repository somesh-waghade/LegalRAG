"""
api.py – FastAPI REST backend for LegalRAG.

Endpoints:
  POST /upload           – Upload and ingest a PDF document
  POST /ask              – Ask a question across all uploaded documents
  GET  /documents        – List all ingested documents
  POST /clear            – Clear all documents and session data
  GET  /health           – Health check
"""

import os
import uuid
import json
import shutil
import logging
from typing import List, Optional
from pathlib import Path

from fastapi import FastAPI, UploadFile, File, HTTPException, Form
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from backend.rag import ingest_document, answer_question
from backend.retriever import clear_all_documents, delete_document

logger = logging.getLogger(__name__)

# ─── App Setup ────────────────────────────────────────────────────────────────

app = FastAPI(
    title="LegalRAG API",
    description="AI-powered legal document analysis via RAG pipeline",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─── Persistent Document Registry ─────────────────────────────────────────────

UPLOADS_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "uploads")
REGISTRY_FILE = os.path.join(UPLOADS_DIR, "registry.json")
os.makedirs(UPLOADS_DIR, exist_ok=True)


def _load_registry() -> dict:
    """Load the document registry from disk."""
    if os.path.exists(REGISTRY_FILE):
        with open(REGISTRY_FILE, "r") as f:
            return json.load(f)
    return {}


def _save_registry(registry: dict):
    """Persist the document registry to disk."""
    with open(REGISTRY_FILE, "w") as f:
        json.dump(registry, f, indent=2)


# ─── Request / Response Models ─────────────────────────────────────────────────

class AskRequest(BaseModel):
    question: str
    n_results: Optional[int] = 5


class SourceCitation(BaseModel):
    source_filename: str
    page_num: int
    excerpt: str


class AskResponse(BaseModel):
    answer: str
    sources: List[SourceCitation]


class DocumentInfo(BaseModel):
    doc_id: str
    filename: str
    num_pages: int
    num_chunks: int


class UploadResponse(BaseModel):
    doc_id: str
    filename: str
    num_pages: int
    num_chunks: int
    message: str


# ─── Endpoints ────────────────────────────────────────────────────────────────

@app.get("/health")
def health_check():
    """Health check endpoint."""
    return {"status": "ok", "service": "LegalRAG API"}


@app.get("/")
@app.head("/")
def root_health_check():
    """Root endpoint for platform health checks."""
    return {"status": "ok", "service": "LegalRAG API"}


@app.post("/upload", response_model=UploadResponse)
async def upload_document(file: UploadFile = File(...)):
    """
    Upload a PDF document and run the full ingestion pipeline.
    Returns a doc_id used to reference this document in future requests.
    """
    original_filename = Path(file.filename or "").name
    if not original_filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are supported.")

    doc_id = str(uuid.uuid4())
    save_path = os.path.join(UPLOADS_DIR, f"{doc_id}_{original_filename}")

    # Save uploaded file
    try:
        with open(save_path, "wb") as f:
            shutil.copyfileobj(file.file, f)
    except Exception as e:
        logger.exception("Failed to save uploaded file")
        raise HTTPException(status_code=500, detail=f"Could not save upload: {str(e)}")

    # Run ingestion pipeline
    try:
        stats = ingest_document(save_path, doc_id)
    except Exception as e:
        logger.exception("Ingestion failed for uploaded file: %s", original_filename)
        if os.path.exists(save_path):
            os.remove(save_path)
        raise HTTPException(status_code=500, detail=f"Ingestion failed: {str(e)}")

    # Register document
    registry = _load_registry()
    registry[doc_id] = {
        "doc_id": doc_id,
        "filename": original_filename,
        "num_pages": stats["num_pages"],
        "num_chunks": stats["num_chunks"],
        "file_path": save_path,
    }
    _save_registry(registry)

    return UploadResponse(
        doc_id=doc_id,
        filename=original_filename,
        num_pages=stats["num_pages"],
        num_chunks=stats["num_chunks"],
        message=f"Successfully processed '{original_filename}' into {stats['num_chunks']} chunks.",
    )


@app.post("/ask", response_model=AskResponse)
def ask(request: AskRequest):
    """
    Answer a question across all uploaded documents simultaneously.
    """
    if not request.question.strip():
        raise HTTPException(status_code=400, detail="Question cannot be empty.")

    try:
        result = answer_question(
            question=request.question,
            n_results=request.n_results,
        )
    except EnvironmentError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"QA pipeline error: {str(e)}")

    return AskResponse(
        answer=result["answer"],
        sources=[SourceCitation(**s) for s in result["sources"]],
    )


@app.get("/documents", response_model=List[DocumentInfo])
def list_documents():
    """List all documents that have been uploaded and processed."""
    registry = _load_registry()
    return [
        DocumentInfo(
            doc_id=v["doc_id"],
            filename=v["filename"],
            num_pages=v["num_pages"],
            num_chunks=v["num_chunks"],
        )
        for v in registry.values()
    ]


@app.post("/clear")
def clear_documents_endpoint():
    """
    Wipe all documents from the vector database, delete the uploaded PDFs, 
    and clear the registry.
    """
    # 1. Wipe vector database
    clear_all_documents()

    # 2. Delete all files in uploads
    registry = _load_registry()
    for doc_info in registry.values():
        file_path = doc_info.get("file_path", "")
        if file_path and os.path.exists(file_path):
            try:
                os.remove(file_path)
            except Exception:
                pass

    # 3. Clear registry
    _save_registry({})
    return {"message": "All documents and session data have been cleared."}


@app.delete("/documents/{doc_id}")
def delete_document_endpoint(doc_id: str):
    """
    Remove a specific document from the unified session collection and registry.
    Also deletes the uploaded PDF file from disk.
    """
    registry = _load_registry()
    if doc_id not in registry:
        raise HTTPException(status_code=404, detail="Document not found.")

    doc_info = registry[doc_id]

    # Remove from unified vector DB
    delete_document(doc_id)

    # Remove PDF file from disk
    file_path = doc_info.get("file_path", "")
    if file_path and os.path.exists(file_path):
        try:
            os.remove(file_path)
        except Exception:
            pass

    # Remove from registry
    del registry[doc_id]
    _save_registry(registry)

    return {"message": f"Document '{doc_info['filename']}' deleted successfully."}
