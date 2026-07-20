# ⚖️ LegalRAG – AI-Powered Legal Document Assistant

> Upload legal documents and ask questions in plain English. Answers are grounded in your documents with source citations.

---

## 🚀 Quick Start

### 1. Clone & Navigate

```bash
cd LegalRAG
```

### 2. Create Virtual Environment

```bash
python -m venv venv
# Windows:
venv\Scripts\activate
# Linux/macOS:
source venv/bin/activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure API Key

```bash
# Copy the example env file
copy .env.example .env    # Windows
cp .env.example .env      # Linux/macOS

# Edit .env and add your API keys
GROQ_API_KEY=your_groq_key_here

# Recommended free demo embedding provider
GEMINI_API_KEY=your_gemini_key_here
EMBEDDING_PROVIDER=auto

# Optional paid alternative for embeddings
OPENAI_API_KEY=your_openai_key_here
```

### 5. Run the Application

```bash
streamlit run app.py
```

The Streamlit app will automatically start the FastAPI backend on port 8000.

**Or run them separately:**

```bash
# Terminal 1 – Backend
uvicorn backend.api:app --host 0.0.0.0 --port 8000 --reload

# Terminal 2 – Frontend
streamlit run app.py
```

---

## 📁 Project Structure

```
LegalRAG/
├── app.py                  # Streamlit frontend
├── requirements.txt        # Python dependencies
├── .env.example            # Environment variable template
│
├── backend/
│   ├── __init__.py
│   ├── api.py              # FastAPI REST endpoints
│   ├── rag.py              # RAG pipeline orchestration
│   ├── embeddings.py       # Sentence-transformers embeddings
│   ├── retriever.py        # ChromaDB vector store
│   └── pdf_reader.py       # PDF text extraction (PyMuPDF)
│
├── uploads/                # Uploaded PDFs (auto-created)
└── vector_db/              # ChromaDB storage (auto-created)
```

---

## 🔌 API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/health` | Health check |
| `POST` | `/upload` | Upload & ingest a PDF |
| `POST` | `/ask` | Ask a question |
| `POST` | `/summarize` | Generate document summary |
| `GET` | `/documents` | List all documents |
| `DELETE` | `/documents/{doc_id}` | Delete a document |

Interactive API docs: **http://localhost:8000/docs**

---

## 🛠️ Technology Stack

| Layer | Technology |
|-------|-----------|
| LLM | Groq |
| Embeddings | Gemini free-tier embeddings, OpenAI optional, Hugging Face fallback, or local fallback |
| Vector DB | ChromaDB (persistent) |
| PDF Parser | PyMuPDF |
| Backend | FastAPI + Uvicorn |
| Frontend | Streamlit |

---

## 💡 Example Questions

- *"What is the termination clause?"*
- *"What are the payment terms?"*
- *"Is there a confidentiality agreement?"*
- *"Who owns the intellectual property?"*
- *"What is the notice period?"*
- *"What are the renewal conditions?"*
- *"Summarize the responsibilities of each party."*

---

## 📝 License

MIT License – free to use and modify.
