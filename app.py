"""
app.py – Streamlit frontend for LegalRAG.

A polished, professional legal document analysis interface with:
  - Document upload and management sidebar
  - Chat interface with conversation history
  - Document summarization tab
  - Source citation display with page badges
"""

import streamlit as st
import requests
import subprocess
import sys
import time
import os
import threading
from datetime import datetime

# ─── Configuration ────────────────────────────────────────────────────────────

API_BASE = os.getenv("FASTAPI_URL", "http://localhost:8000")

# ─── Page Config ──────────────────────────────────────────────────────────────

st.set_page_config(
    page_title="LegalRAG – AI Legal Assistant",
    page_icon="⚖️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─── Custom CSS ───────────────────────────────────────────────────────────────

st.markdown("""
<style>
  @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=Playfair+Display:wght@600;700&display=swap');

  /* ── Global Reset ── */
  html, body, [class*="css"] {
    font-family: 'Inter', sans-serif;
  }

  /* ── Dark Background ── */
  .stApp {
    background: linear-gradient(135deg, #0a0e1a 0%, #0f1629 50%, #0a0e1a 100%);
    color: #e8eaf0;
  }

  /* ── Hide Streamlit Branding (surgical – never hide sidebar controls) ── */
  #MainMenu { display: none !important; }
  footer { display: none !important; }
  [data-testid="stToolbar"] { display: none !important; }
  [data-testid="stDecoration"] { display: none !important; }
  [data-testid="stStatusWidget"] { display: none !important; }
  .block-container { padding-top: 1.5rem; padding-bottom: 2rem; }

  /* ── Sidebar collapsed-toggle – make it always visible ── */
  [data-testid="collapsedControl"],
  [data-testid="stSidebarCollapsedControl"] {
    display: flex !important;
    visibility: visible !important;
    opacity: 1 !important;
    z-index: 99999 !important;
    background: rgba(212, 175, 55, 0.15) !important;
    border-radius: 0 8px 8px 0 !important;
    border: 1px solid rgba(212, 175, 55, 0.4) !important;
    border-left: none !important;
  }
  [data-testid="collapsedControl"] button,
  [data-testid="stSidebarCollapsedControl"] button {
    color: #d4af37 !important;
    visibility: visible !important;
  }
  [data-testid="collapsedControl"] svg,
  [data-testid="stSidebarCollapsedControl"] svg {
    fill: #d4af37 !important;
    stroke: #d4af37 !important;
    visibility: visible !important;
  }

  /* ── Sidebar ── */
  [data-testid="stSidebar"] {
    background: linear-gradient(180deg, #0d1224 0%, #111827 100%);
    border-right: 1px solid rgba(212, 175, 55, 0.2);
  }
  [data-testid="stSidebar"] .stMarkdown h1,
  [data-testid="stSidebar"] .stMarkdown h2,
  [data-testid="stSidebar"] .stMarkdown h3 {
    color: #d4af37;
  }

  /* ── Logo Header ── */
  .logo-header {
    text-align: center;
    padding: 1.5rem 0 1rem;
    border-bottom: 1px solid rgba(212, 175, 55, 0.2);
    margin-bottom: 1.5rem;
  }
  .logo-title {
    font-family: 'Playfair Display', serif;
    font-size: 1.8rem;
    font-weight: 700;
    background: linear-gradient(135deg, #d4af37, #f0d060, #d4af37);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
    letter-spacing: 0.05em;
  }
  .logo-subtitle {
    font-size: 0.72rem;
    color: #8892a4;
    letter-spacing: 0.12em;
    text-transform: uppercase;
    margin-top: 0.3rem;
  }

  /* ── Status Badge ── */
  .status-badge {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    padding: 4px 12px;
    border-radius: 20px;
    font-size: 0.72rem;
    font-weight: 600;
    letter-spacing: 0.05em;
    text-transform: uppercase;
  }
  .status-online {
    background: rgba(34, 197, 94, 0.12);
    color: #22c55e;
    border: 1px solid rgba(34, 197, 94, 0.3);
  }
  .status-offline {
    background: rgba(239, 68, 68, 0.12);
    color: #ef4444;
    border: 1px solid rgba(239, 68, 68, 0.3);
  }

  /* ── Document Card ── */
  .doc-card {
    background: rgba(255,255,255,0.03);
    border: 1px solid rgba(212, 175, 55, 0.15);
    border-radius: 10px;
    padding: 12px 14px;
    margin-bottom: 10px;
    transition: border-color 0.2s;
  }
  .doc-card:hover { border-color: rgba(212, 175, 55, 0.4); }
  .doc-card-title {
    font-weight: 600;
    font-size: 0.85rem;
    color: #d4af37;
    margin-bottom: 4px;
    word-break: break-all;
  }
  .doc-card-meta {
    font-size: 0.72rem;
    color: #6b7a99;
  }
  .doc-card-active {
    border-color: rgba(212, 175, 55, 0.6) !important;
    background: rgba(212, 175, 55, 0.07) !important;
  }

  /* ── Chat Messages ── */
  .chat-container {
    display: flex;
    flex-direction: column;
    gap: 16px;
    padding: 0 0 1rem;
  }
  .chat-bubble {
    max-width: 78%;
    padding: 14px 18px;
    border-radius: 16px;
    line-height: 1.65;
    font-size: 0.9rem;
    animation: fadeUp 0.3s ease;
  }
  @keyframes fadeUp {
    from { opacity: 0; transform: translateY(8px); }
    to   { opacity: 1; transform: translateY(0); }
  }
  .user-bubble {
    align-self: flex-end;
    margin-left: auto;
    background: linear-gradient(135deg, #1e3a5f, #1a2d4a);
    border: 1px solid rgba(100, 160, 255, 0.25);
    color: #ccd6f6;
  }
  .ai-bubble {
    align-self: flex-start;
    background: rgba(255,255,255,0.04);
    border: 1px solid rgba(212, 175, 55, 0.2);
    color: #e0e6f0;
  }
  .bubble-label {
    font-size: 0.68rem;
    font-weight: 700;
    letter-spacing: 0.1em;
    text-transform: uppercase;
    margin-bottom: 6px;
    opacity: 0.6;
  }

  /* ── Source Citation Cards ── */
  .source-card {
    background: rgba(212, 175, 55, 0.06);
    border: 1px solid rgba(212, 175, 55, 0.2);
    border-left: 3px solid #d4af37;
    border-radius: 8px;
    padding: 10px 14px;
    margin-top: 6px;
    font-size: 0.8rem;
  }
  .source-header {
    display: flex;
    align-items: center;
    gap: 8px;
    margin-bottom: 6px;
  }
  .page-badge {
    background: linear-gradient(135deg, #d4af37, #b8962e);
    color: #0a0e1a;
    padding: 2px 8px;
    border-radius: 10px;
    font-size: 0.68rem;
    font-weight: 700;
    letter-spacing: 0.05em;
  }
  .source-filename {
    color: #8892a4;
    font-size: 0.75rem;
    font-style: italic;
  }
  .source-excerpt {
    color: #9aa3b5;
    font-size: 0.78rem;
    line-height: 1.5;
    font-style: italic;
    border-top: 1px solid rgba(255,255,255,0.05);
    padding-top: 6px;
    margin-top: 4px;
  }

  /* ── Section Headers ── */
  .section-header {
    font-family: 'Playfair Display', serif;
    font-size: 1.6rem;
    font-weight: 700;
    background: linear-gradient(135deg, #d4af37, #f0d060);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
    margin-bottom: 0.3rem;
  }
  .section-sub {
    color: #6b7a99;
    font-size: 0.85rem;
    margin-bottom: 1.5rem;
  }

  /* ── Welcome Banner ── */
  .welcome-banner {
    background: linear-gradient(135deg, rgba(212,175,55,0.07), rgba(100,160,255,0.05));
    border: 1px solid rgba(212,175,55,0.2);
    border-radius: 16px;
    padding: 2.5rem;
    text-align: center;
    margin: 2rem 0;
  }
  .welcome-icon { font-size: 3.5rem; margin-bottom: 1rem; }
  .welcome-title {
    font-family: 'Playfair Display', serif;
    font-size: 1.9rem;
    font-weight: 700;
    color: #d4af37;
    margin-bottom: 0.6rem;
  }
  .welcome-desc { color: #8892a4; font-size: 0.9rem; line-height: 1.7; }
  .feature-grid {
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 12px;
    margin-top: 1.8rem;
    text-align: left;
  }
  .feature-item {
    background: rgba(255,255,255,0.03);
    border: 1px solid rgba(255,255,255,0.08);
    border-radius: 10px;
    padding: 14px;
  }
  .feature-icon { font-size: 1.4rem; margin-bottom: 6px; }
  .feature-title { font-weight: 600; font-size: 0.82rem; color: #ccd6f6; margin-bottom: 3px; }
  .feature-desc  { font-size: 0.74rem; color: #6b7a99; }

  /* ── Summary Box ── */
  .summary-box {
    background: rgba(255,255,255,0.03);
    border: 1px solid rgba(212,175,55,0.2);
    border-radius: 12px;
    padding: 1.5rem 1.8rem;
    line-height: 1.8;
    font-size: 0.9rem;
    color: #d0d8e8;
  }

  /* ── Buttons ── */
  .stButton > button {
    width: 100%;
    background: linear-gradient(135deg, #d4af37, #b8962e);
    color: #0a0e1a;
    font-weight: 700;
    border: none;
    border-radius: 8px;
    padding: 0.6rem 1rem;
    font-family: 'Inter', sans-serif;
    letter-spacing: 0.03em;
    transition: opacity 0.2s, transform 0.1s;
  }
  .stButton > button:hover { opacity: 0.88; transform: translateY(-1px); }
  .stButton > button:active { transform: translateY(0); }

  /* ── File Uploader ── */
  [data-testid="stFileUploader"] {
    border: 2px dashed rgba(212,175,55,0.3);
    border-radius: 10px;
    padding: 0.5rem;
    transition: border-color 0.2s;
  }
  [data-testid="stFileUploader"]:hover { border-color: rgba(212,175,55,0.6); }

  /* ── Input Field ── */
  .stTextInput > div > div > input,
  .stTextArea textarea {
    background: rgba(255,255,255,0.04) !important;
    border: 1px solid rgba(212,175,55,0.2) !important;
    border-radius: 8px !important;
    color: #e8eaf0 !important;
    font-family: 'Inter', sans-serif !important;
  }
  .stTextInput > div > div > input:focus,
  .stTextArea textarea:focus {
    border-color: rgba(212,175,55,0.6) !important;
    box-shadow: 0 0 0 2px rgba(212,175,55,0.1) !important;
  }

  /* ── Select Box ── */
  .stSelectbox > div > div {
    background: rgba(255,255,255,0.04) !important;
    border: 1px solid rgba(212,175,55,0.2) !important;
    border-radius: 8px !important;
    color: #e8eaf0 !important;
  }

  /* ── Tabs ── */
  .stTabs [data-baseweb="tab-list"] {
    background: rgba(255,255,255,0.03);
    border-radius: 10px;
    padding: 4px;
    gap: 4px;
    border: 1px solid rgba(255,255,255,0.07);
  }
  .stTabs [data-baseweb="tab"] {
    border-radius: 7px;
    color: #6b7a99;
    font-weight: 500;
    padding: 8px 20px;
    font-family: 'Inter', sans-serif;
  }
  .stTabs [aria-selected="true"] {
    background: linear-gradient(135deg, rgba(212,175,55,0.15), rgba(212,175,55,0.08)) !important;
    color: #d4af37 !important;
    border: 1px solid rgba(212,175,55,0.3) !important;
  }

  /* ── Divider ── */
  hr { border-color: rgba(255,255,255,0.06); margin: 1rem 0; }

  /* ── Spinner ── */
  .stSpinner > div { border-top-color: #d4af37 !important; }

  /* ── Success/Error Alerts ── */
  .stSuccess { background: rgba(34,197,94,0.1) !important; border: 1px solid rgba(34,197,94,0.3) !important; border-radius: 8px; }
  .stError   { background: rgba(239,68,68,0.1)  !important; border: 1px solid rgba(239,68,68,0.3)  !important; border-radius: 8px; }
  .stInfo    { background: rgba(99,179,237,0.08) !important; border: 1px solid rgba(99,179,237,0.25) !important; border-radius: 8px; }
  .stWarning { background: rgba(251,191,36,0.08) !important; border: 1px solid rgba(251,191,36,0.25) !important; border-radius: 8px; }

  /* ── Radio ── */
  .stRadio > div { gap: 12px; }
  .stRadio label { color: #9aa3b5 !important; }

  /* ── Scrollbar ── */
  ::-webkit-scrollbar { width: 6px; height: 6px; }
  ::-webkit-scrollbar-track { background: rgba(255,255,255,0.03); }
  ::-webkit-scrollbar-thumb { background: rgba(212,175,55,0.3); border-radius: 3px; }
  ::-webkit-scrollbar-thumb:hover { background: rgba(212,175,55,0.5); }
</style>
""", unsafe_allow_html=True)

# ─── Auto-open sidebar on every page load ────────────────────────────────────
st.markdown("""
<script>
(function openSidebar() {
    var attempts = 0;
    var maxAttempts = 20;  // try for ~6 seconds
    var timer = setInterval(function() {
        attempts++;
        var doc = window.parent.document;

        // Check if sidebar is collapsed
        var sidebar = doc.querySelector('[data-testid="stSidebar"]');
        if (!sidebar) { if (attempts >= maxAttempts) clearInterval(timer); return; }

        var isCollapsed = sidebar.getAttribute('aria-expanded') === 'false'
                       || sidebar.classList.contains('st-emotion-cache-collapsed')
                       || sidebar.style.width === '0px'
                       || sidebar.offsetWidth < 50;

        // Find the expand button (try multiple selectors across Streamlit versions)
        var btn = doc.querySelector('[data-testid="collapsedControl"] button')
               || doc.querySelector('[data-testid="stSidebarCollapsedControl"] button')
               || doc.querySelector('button[kind="header"][aria-label*="sidebar"]')
               || doc.querySelector('[data-testid="stSidebar"] ~ * button');

        if (isCollapsed && btn) {
            btn.click();
            clearInterval(timer);
        } else if (!isCollapsed) {
            clearInterval(timer);  // already open, done
        }

        if (attempts >= maxAttempts) clearInterval(timer);
    }, 300);
})();
</script>
""", unsafe_allow_html=True)

# ─── Helper: API calls ────────────────────────────────────────────────────────

def api_health() -> bool:
    try:
        r = requests.get(f"{API_BASE}/health", timeout=3)
        return r.status_code == 200
    except Exception:
        return False


def api_upload(file_bytes: bytes, filename: str) -> dict:
    files = {"file": (filename, file_bytes, "application/pdf")}
    r = requests.post(f"{API_BASE}/upload", files=files, timeout=120)
    r.raise_for_status()
    return r.json()


def api_ask(question: str) -> dict:
    payload = {"question": question, "n_results": 5}
    r = requests.post(f"{API_BASE}/ask", json=payload, timeout=60)
    r.raise_for_status()
    return r.json()


def api_list_documents() -> list:
    try:
        r = requests.get(f"{API_BASE}/documents", timeout=10)
        r.raise_for_status()
        return r.json()
    except Exception:
        return []


def api_clear() -> bool:
    try:
        r = requests.post(f"{API_BASE}/clear", timeout=10)
        return r.status_code == 200
    except Exception:
        return False

def api_delete_document(doc_id: str) -> bool:
    try:
        r = requests.delete(f"{API_BASE}/documents/{doc_id}", timeout=10)
        return r.status_code == 200
    except Exception:
        return False


# ─── Session State Init ───────────────────────────────────────────────────────

if "chat_history" not in st.session_state:
    st.session_state.chat_history = []  # list of {role, content, sources, timestamp}

if "documents" not in st.session_state:
    st.session_state.documents = []

if "api_online" not in st.session_state:
    st.session_state.api_online = False


# ─── Auto-start FastAPI backend ───────────────────────────────────────────────

def start_backend():
    """Start FastAPI backend as a subprocess if not already running."""
    if not api_health():
        subprocess.Popen(
            [sys.executable, "-m", "uvicorn", "backend.api:app",
             "--host", "0.0.0.0", "--port", "8000", "--log-level", "warning"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            cwd=os.path.dirname(__file__),
        )
        # Wait up to 8 seconds for it to start
        for _ in range(16):
            time.sleep(0.5)
            if api_health():
                break

if "backend_started" not in st.session_state:
    st.session_state.backend_started = True
    threading.Thread(target=start_backend, daemon=True).start()


# ─── Refresh documents & API status ──────────────────────────────────────────

st.session_state.api_online = api_health()
if st.session_state.api_online:
    st.session_state.documents = api_list_documents()


# ═══════════════════════════════════════════════════════════════════════════════
#  SIDEBAR
# ═══════════════════════════════════════════════════════════════════════════════

with st.sidebar:
    # Logo
    st.markdown("""
    <div class="logo-header">
      <div class="logo-title">⚖️ LegalRAG</div>
      <div class="logo-subtitle">AI Legal Document Assistant</div>
    </div>
    """, unsafe_allow_html=True)

    # API Status
    if st.session_state.api_online:
        st.markdown('<div class="status-badge status-online">● API Online</div>', unsafe_allow_html=True)
    else:
        st.markdown('<div class="status-badge status-offline">● API Offline – Starting…</div>', unsafe_allow_html=True)
        if st.button("🔄 Retry Connection"):
            st.rerun()

    st.markdown("---")

    # ── Upload Section ──
    st.markdown("### 📄 Upload Document")
    uploaded_file = st.file_uploader(
        "Choose a PDF file",
        type=["pdf"],
        help="Upload a legal document (contract, NDA, policy, etc.)",
        label_visibility="collapsed",
    )

    if uploaded_file and st.session_state.api_online:
        if st.button("⬆️ Process Document", key="upload_btn"):
            with st.spinner(f"Processing '{uploaded_file.name}'…"):
                try:
                    result = api_upload(uploaded_file.getvalue(), uploaded_file.name)
                    st.success(f"✓ {result['num_chunks']} chunks indexed from {result['num_pages']} pages")
                    st.session_state.chat_history = []
                    st.session_state.documents = api_list_documents()
                    st.rerun()
                except requests.HTTPError as e:
                    st.error(f"Upload failed: {e.response.text}")
                except Exception as e:
                    st.error(f"Error: {str(e)}")
    elif uploaded_file and not st.session_state.api_online:
        st.warning("API is not online. Please wait for it to start.")

    st.markdown("---")

    # ── Document Library ──
    st.markdown("### 📚 Document Library")

    if not st.session_state.documents:
        st.markdown(
            '<div style="color:#4a5568;font-size:0.82rem;text-align:center;padding:1rem 0;">'
            'No documents yet.<br>Upload a PDF to get started.'
            '</div>',
            unsafe_allow_html=True,
        )
    else:
        for doc in st.session_state.documents:
            st.markdown(f"""
            <div class="doc-card">
              <div class="doc-card-title">📋 {doc['filename']}</div>
              <div class="doc-card-meta">{doc['num_pages']} pages · {doc['num_chunks']} chunks</div>
            </div>
            """, unsafe_allow_html=True)
            if st.button("🗑️ Remove", key=f"del_side_{doc['doc_id']}", help="Delete this document"):
                if api_delete_document(doc["doc_id"]):
                    st.session_state.documents = api_list_documents()
                    st.rerun()

        # Clear all button
        if st.button("🗑️ Clear All Documents", help="Remove all uploaded documents"):
            api_clear()
            st.session_state.chat_history = []
            st.session_state.documents = []
            st.rerun()

    st.markdown("---")

    # ── Clear Chat ──
    if st.session_state.chat_history:
        if st.button("🗑️ Clear Conversation"):
            st.session_state.chat_history = []
            st.rerun()

    # ── Footer ──
    st.markdown("""
    <div style="text-align:center;color:#3a4460;font-size:0.7rem;padding-top:1rem;">
      LegalRAG v1.0 · Powered by Gemini AI<br>
      <span style="color:#2a3050;">Answers grounded in your documents</span>
    </div>
    """, unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════════════════════
#  MAIN CONTENT
# ═══════════════════════════════════════════════════════════════════════════════

# ── Top bar ──
top_left, top_right = st.columns([3, 1])
with top_left:
    st.markdown("""
    <div class="section-header">⚖️ LegalRAG</div>
    <div class="section-sub">AI-Powered Legal Document Assistant</div>
    """, unsafe_allow_html=True)

with top_right:
    if st.session_state.documents and st.button("🔄 New Chat"):
        st.session_state.chat_history = []
        st.rerun()

# ── Upload expander (always accessible, even when sidebar is collapsed) ──
with st.expander("📂 Upload Document / Document Library", expanded=not bool(st.session_state.documents)):
    up_col, lib_col = st.columns([1, 1])

    with up_col:
        st.markdown("**📄 Upload a PDF**")
        exp_uploaded = st.file_uploader(
            "Choose a PDF file",
            type=["pdf"],
            key="main_uploader",
            label_visibility="collapsed",
        )
        if exp_uploaded and st.session_state.api_online:
            if st.button("⬆️ Process Document", key="main_upload_btn"):
                with st.spinner(f"Processing '{exp_uploaded.name}'…"):
                    try:
                        result = api_upload(exp_uploaded.getvalue(), exp_uploaded.name)
                        st.success(f"✓ {result['num_chunks']} chunks indexed from {result['num_pages']} pages")
                        st.session_state.chat_history = []
                        st.session_state.documents = api_list_documents()
                        st.rerun()
                    except Exception as e:
                        st.error(f"Upload failed: {str(e)}")
        elif exp_uploaded and not st.session_state.api_online:
            st.warning("API is offline. Please wait for it to start.")

    with lib_col:
        st.markdown("**📚 Document Library**")
        if not st.session_state.documents:
            st.caption("No documents yet. Upload a PDF to get started.")
        else:
            for doc in st.session_state.documents:
                c1, c2 = st.columns([4, 1])
                with c1:
                    st.markdown(f"✅ {doc['filename']}")
                with c2:
                    if st.button("🗑️", key=f"del_exp_{doc['doc_id']}", help="Delete"):
                        if api_delete_document(doc["doc_id"]):
                            st.session_state.documents = api_list_documents()
                            st.rerun()

# ── Tabs ──
tab_chat, tab_about = st.tabs(["💬  Chat", "ℹ️  About"])


# ════════════════════════════════
#  TAB 1 – CHAT
# ════════════════════════════════

with tab_chat:

    # ── Welcome Banner (only when no doc selected) ──
    if not st.session_state.documents:
        st.markdown("""
        <div class="welcome-banner">
          <div class="welcome-icon">⚖️</div>
          <div class="welcome-title">Welcome to LegalRAG</div>
          <div class="welcome-desc">
            Upload a legal document from the sidebar or the panel above to start asking questions.<br>
            Our AI will analyze your document and provide accurate, cited answers.
          </div>
          <div class="feature-grid">
            <div class="feature-item">
              <div class="feature-icon">🔍</div>
              <div class="feature-title">Semantic Search</div>
              <div class="feature-desc">Finds relevant clauses even when you don't know the exact wording</div>
            </div>
            <div class="feature-item">
              <div class="feature-icon">💡</div>
              <div class="feature-title">Plain English Answers</div>
              <div class="feature-desc">Complex legal language explained in simple terms</div>
            </div>
            <div class="feature-item">
              <div class="feature-icon">📌</div>
              <div class="feature-title">Source Citations</div>
              <div class="feature-desc">Every answer links back to the exact page in your document</div>
            </div>
          </div>
        </div>
        """, unsafe_allow_html=True)

        st.markdown("#### 💡 Example Questions You Can Ask")
        example_cols = st.columns(3)
        examples = [
            ("📋 Termination", "What is the termination clause?"),
            ("💰 Payment", "What are the payment terms?"),
            ("🔒 Confidentiality", "Is there a confidentiality agreement?"),
            ("⏰ Notice Period", "What is the notice period?"),
            ("🏛️ IP Rights", "Who owns the intellectual property?"),
            ("🔄 Renewal", "What are the renewal conditions?"),
        ]
        for i, (label, q) in enumerate(examples):
            with example_cols[i % 3]:
                st.markdown(f"""
                <div style="background:rgba(255,255,255,0.03);border:1px solid rgba(255,255,255,0.08);
                     border-radius:8px;padding:12px;margin-bottom:8px;font-size:0.82rem;color:#8892a4;">
                  <strong style="color:#d4af37;">{label}</strong><br>
                  <em>"{q}"</em>
                </div>
                """, unsafe_allow_html=True)

    # ── Chat History ──
    if st.session_state.chat_history:
        chat_html = '<div class="chat-container">'
        for msg in st.session_state.chat_history:
            if msg["role"] == "user":
                ts = msg.get("timestamp", "")
                chat_html += f"""
                    <div style="display:flex;justify-content:flex-end;">
                      <div class="chat-bubble user-bubble">
                        <div class="bubble-label" style="text-align:right;">You · {ts}</div>
                        {msg['content']}
                      </div>
                    </div>"""
            else:
                ts = msg.get("timestamp", "")
                chat_html += f"""
                    <div style="display:flex;justify-content:flex-start;">
                      <div class="chat-bubble ai-bubble">
                        <div class="bubble-label">⚖️ LegalRAG · {ts}</div>
                        {msg['content'].replace(chr(10), '<br>')}
                      </div>
                    </div>"""
        chat_html += "</div>"
        st.markdown(chat_html, unsafe_allow_html=True)

        # ── Source Citations ──
        last_ai = next(
            (m for m in reversed(st.session_state.chat_history) if m["role"] == "assistant"),
            None,
        )
        if last_ai and last_ai.get("sources"):
            with st.expander(f"📌 Sources ({len(last_ai['sources'])} references)", expanded=False):
                for src in last_ai["sources"]:
                    st.markdown(f"""
                    <div class="source-card">
                      <div class="source-header">
                        <span class="page-badge">Page {src['page_num']}</span>
                        <span class="source-filename">📄 {src['source_filename']}</span>
                      </div>
                      <div class="source-excerpt">"{src['excerpt']}"</div>
                    </div>
                    """, unsafe_allow_html=True)

    elif st.session_state.documents:
        st.markdown("""
        <div style="text-align:center;padding:2rem;color:#4a5568;">
          <div style="font-size:2rem;margin-bottom:0.5rem;">💬</div>
          <div style="font-size:0.9rem;">Ask anything about your document.</div>
          <div style="font-size:0.78rem;margin-top:0.3rem;color:#3a4460;">
            Try: "What is the termination clause?" or "Summarize the key terms"
          </div>
        </div>
        """, unsafe_allow_html=True)

        # ── Quick-question pills ──
        st.markdown(
            '<div style="font-size:0.78rem;color:#4a5568;margin-bottom:6px;">Quick questions:</div>',
            unsafe_allow_html=True,
        )
        quick_qs = [
            "What is the termination clause?",
            "What are the payment terms?",
            "Is there a confidentiality agreement?",
            "What are the responsibilities of each party?",
        ]
        q_cols = st.columns(len(quick_qs))
        for i, qq in enumerate(quick_qs):
            with q_cols[i]:
                if st.button(qq, key=f"quick_{i}"):
                    ts = datetime.now().strftime("%H:%M")
                    st.session_state.chat_history.append({
                        "role": "user", "content": qq, "timestamp": ts, "sources": [],
                    })
                    with st.spinner("🔍 Searching…"):
                        try:
                            result = api_ask(qq)
                            st.session_state.chat_history.append({
                                "role": "assistant", "content": result["answer"],
                                "timestamp": ts, "sources": result.get("sources", []),
                            })
                        except Exception as e:
                            st.session_state.chat_history.append({
                                "role": "assistant", "content": f"❌ **Error**: {str(e)}",
                                "timestamp": ts, "sources": [],
                            })
                    st.rerun()

    st.markdown("---")

    # ── Question Input (always shown) ──
    with st.form(key="chat_form", clear_on_submit=True):
        q_col, btn_col = st.columns([6, 1])
        with q_col:
            question = st.text_input(
                "Ask a question",
                placeholder="Upload a document above, then ask your question…" if not st.session_state.documents else "e.g. What are the termination conditions?",
                label_visibility="collapsed",
                key="question_input",
            )
        with btn_col:
            submitted = st.form_submit_button("Ask ➤")

    if submitted and question.strip():
        if not st.session_state.api_online:
            st.error("API is not online. Please wait for it to start and try again.")
        elif not st.session_state.documents:
            st.warning("⬆️ Please upload a document first before asking questions.")
        else:
            ts = datetime.now().strftime("%H:%M")
            st.session_state.chat_history.append({
                "role": "user", "content": question, "timestamp": ts, "sources": [],
            })
            with st.spinner("🔍 Searching document and generating answer…"):
                try:
                    result = api_ask(question)
                    st.session_state.chat_history.append({
                        "role": "assistant", "content": result["answer"],
                        "timestamp": ts, "sources": result.get("sources", []),
                    })
                except requests.HTTPError as e:
                    st.session_state.chat_history.append({
                        "role": "assistant",
                        "content": f"❌ **API Error**: {e.response.text}",
                        "timestamp": ts, "sources": [],
                    })
                except Exception as e:
                    st.session_state.chat_history.append({
                        "role": "assistant",
                        "content": f"❌ **Error**: {str(e)}",
                        "timestamp": ts, "sources": [],
                    })
            st.rerun()


# ════════════════════════════════
#  TAB 2 – ABOUT
# ════════════════════════════════

with tab_about:
    col1, col2 = st.columns([3, 2])

    with col1:
        st.markdown("""
        <div class="section-header" style="font-size:1.4rem;">About LegalRAG</div>
        <div class="section-sub">AI-powered legal document analysis using Retrieval-Augmented Generation</div>
        """, unsafe_allow_html=True)

        st.markdown("""
        <div class="summary-box">
          <strong style="color:#d4af37;">What is LegalRAG?</strong><br><br>
          LegalRAG is an intelligent legal document assistant that uses Retrieval-Augmented Generation (RAG)
          to help you understand complex legal documents without reading every page manually.<br><br>

          <strong style="color:#d4af37;">How It Works</strong><br>
          <ol style="color:#9aa3b5;line-height:2;">
            <li>📄 <strong>Upload</strong> your PDF legal document</li>
            <li>🔪 The text is <strong>extracted and chunked</strong> into segments</li>
            <li>🧠 Each chunk is <strong>embedded</strong> using a neural model</li>
            <li>💾 Embeddings are <strong>stored in ChromaDB</strong> (vector database)</li>
            <li>❓ You <strong>ask a question</strong> in plain English</li>
            <li>🔍 The most <strong>relevant chunks are retrieved</strong> semantically</li>
            <li>🤖 Gemini AI <strong>generates a grounded answer</strong> from those chunks</li>
            <li>📌 <strong>Source citations</strong> show exactly where the answer came from</li>
          </ol>

          <strong style="color:#d4af37;">Why RAG?</strong><br>
          Traditional AI chatbots answer from training data, which doesn't include your private documents.
          RAG grounds every answer in your uploaded document, reducing hallucinations and improving accuracy.
        </div>
        """, unsafe_allow_html=True)

    with col2:
        st.markdown("""
        <div class="section-header" style="font-size:1.2rem;margin-top:0;">Technology Stack</div>
        """, unsafe_allow_html=True)

        stack = [
            ("🧠", "LLM", "Google Gemini 1.5 Flash"),
            ("🔢", "Embeddings", "all-MiniLM-L6-v2"),
            ("💾", "Vector DB", "ChromaDB (persistent)"),
            ("📄", "PDF Parser", "PyMuPDF (fitz)"),
            ("⚡", "Backend", "FastAPI + Uvicorn"),
            ("🎨", "Frontend", "Streamlit"),
            ("🐍", "Language", "Python 3.10+"),
        ]

        for icon, label, tech in stack:
            st.markdown(f"""
            <div style="display:flex;align-items:center;gap:12px;padding:10px 14px;
                        background:rgba(255,255,255,0.03);border:1px solid rgba(255,255,255,0.07);
                        border-radius:8px;margin-bottom:8px;">
              <span style="font-size:1.2rem;">{icon}</span>
              <div>
                <div style="font-size:0.7rem;color:#6b7a99;text-transform:uppercase;letter-spacing:0.08em;">{label}</div>
                <div style="font-size:0.85rem;font-weight:600;color:#ccd6f6;">{tech}</div>
              </div>
            </div>
            """, unsafe_allow_html=True)

        st.markdown("""
        <div style="background:rgba(212,175,55,0.06);border:1px solid rgba(212,175,55,0.2);
             border-radius:10px;padding:14px;margin-top:16px;">
          <div style="color:#d4af37;font-weight:600;font-size:0.85rem;margin-bottom:8px;">📋 Supported Document Types</div>
          <div style="color:#8892a4;font-size:0.8rem;line-height:1.9;">
            • Employment Contracts<br>
            • NDAs & Confidentiality Agreements<br>
            • Lease & Rental Agreements<br>
            • Service Agreements<br>
            • Terms & Conditions<br>
            • Company Policies<br>
            • Partnership Agreements
          </div>
        </div>
        """, unsafe_allow_html=True)
