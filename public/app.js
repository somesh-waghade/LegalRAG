document.addEventListener('DOMContentLoaded', () => {
  // Elements
  const apiStatusBadge = document.getElementById('apiStatusBadge');
  const apiStatusText = document.getElementById('apiStatusText');
  const fileInput = document.getElementById('fileInput');
  const dropZone = document.getElementById('dropZone');
  const progressContainer = document.getElementById('progressContainer');
  const progressBar = document.getElementById('progressBar');
  const progressLabel = document.getElementById('progressLabel');
  const docList = document.getElementById('docList');
  const btnClearAll = document.getElementById('btnClearAll');
  const btnClearChat = document.getElementById('btnClearChat');
  const welcomeContainer = document.getElementById('welcomeContainer');
  const chatContainer = document.getElementById('chatContainer');
  const chatForm = document.getElementById('chatForm');
  const chatInput = document.getElementById('chatInput');
  const btnSend = document.getElementById('btnSend');

  let apiOnline = false;
  let documents = [];
  let chatHistory = [];

  // ─── API Health Check ───
  async function checkApiHealth() {
    try {
      const response = await fetch('/api/health');
      if (response.ok) {
        setApiStatus(true, 'API Online');
      } else {
        setApiStatus(false, 'API Offline');
      }
    } catch (error) {
      setApiStatus(false, 'API Connection Failed');
    }
  }

  function setApiStatus(online, text) {
    apiOnline = online;
    apiStatusText.textContent = text;
    if (online) {
      apiStatusBadge.className = 'status-badge status-online';
      chatInput.disabled = false;
      btnSend.disabled = false;
      loadDocuments();
    } else {
      apiStatusBadge.className = 'status-badge status-offline';
      chatInput.disabled = true;
      btnSend.disabled = true;
    }
  }

  // ─── Document Management ───
  async function loadDocuments() {
    try {
      const response = await fetch('/api/documents');
      if (response.ok) {
        documents = await response.json();
        renderDocuments();
      }
    } catch (error) {
      console.error('Failed to load documents:', error);
    }
  }

  function renderDocuments() {
    docList.innerHTML = '';
    
    if (documents.length === 0) {
      docList.innerHTML = '<div class="empty-state">No documents uploaded yet.</div>';
      btnClearAll.style.display = 'none';
      if (chatHistory.length === 0) {
        welcomeContainer.style.display = 'flex';
        chatContainer.style.display = 'none';
      }
      return;
    }

    btnClearAll.style.display = 'block';

    documents.forEach(doc => {
      const card = document.createElement('div');
      card.className = 'doc-card';
      
      const title = document.createElement('div');
      title.className = 'doc-card-title';
      title.textContent = `📋 ${doc.filename}`;
      title.title = doc.filename;

      const meta = document.createElement('div');
      meta.className = 'doc-card-meta';
      meta.textContent = `${doc.num_pages} pages · ${doc.num_chunks} chunks`;

      const deleteBtn = document.createElement('button');
      deleteBtn.className = 'doc-card-delete';
      deleteBtn.innerHTML = '🗑️';
      deleteBtn.title = 'Remove document';
      deleteBtn.addEventListener('click', async (e) => {
        e.stopPropagation();
        if (confirm(`Are you sure you want to remove ${doc.filename}?`)) {
          await deleteDocument(doc.doc_id);
        }
      });

      card.appendChild(title);
      card.appendChild(meta);
      card.appendChild(deleteBtn);
      docList.appendChild(card);
    });
  }

  async function deleteDocument(docId) {
    try {
      const response = await fetch(`/api/documents/${docId}`, {
        method: 'DELETE'
      });
      if (response.ok) {
        await loadDocuments();
      } else {
        alert('Failed to delete document.');
      }
    } catch (error) {
      console.error('Error deleting document:', error);
    }
  }

  async function clearAllDocuments() {
    if (!confirm('Are you sure you want to delete all documents? This will also clear your chat history.')) {
      return;
    }
    try {
      const response = await fetch('/api/clear', {
        method: 'POST'
      });
      if (response.ok) {
        documents = [];
        chatHistory = [];
        renderDocuments();
        renderChat();
      } else {
        alert('Failed to clear documents.');
      }
    } catch (error) {
      console.error('Error clearing documents:', error);
    }
  }

  // ─── File Upload Handler ───
  dropZone.addEventListener('click', () => fileInput.click());

  dropZone.addEventListener('dragover', (e) => {
    e.preventDefault();
    dropZone.style.background = 'rgba(212, 175, 55, 0.08)';
    dropZone.style.borderColor = '#d4af37';
  });

  dropZone.addEventListener('dragleave', () => {
    dropZone.style.background = 'rgba(212, 175, 55, 0.03)';
    dropZone.style.borderColor = 'rgba(212, 175, 55, 0.3)';
  });

  dropZone.addEventListener('drop', (e) => {
    e.preventDefault();
    dropZone.style.background = 'rgba(212, 175, 55, 0.03)';
    dropZone.style.borderColor = 'rgba(212, 175, 55, 0.3)';
    if (e.dataTransfer.files.length > 0) {
      handleUpload(e.dataTransfer.files[0]);
    }
  });

  fileInput.addEventListener('change', () => {
    if (fileInput.files.length > 0) {
      handleUpload(fileInput.files[0]);
    }
  });

  async function handleUpload(file) {
    if (!apiOnline) {
      alert('API is offline. Cannot upload file.');
      return;
    }
    if (file.type !== 'application/pdf') {
      alert('Only PDF files are supported.');
      return;
    }

    progressContainer.style.display = 'block';
    progressBar.style.width = '0%';
    progressLabel.textContent = `Uploading '${file.name}'...`;

    const formData = new FormData();
    formData.append('file', file);

    try {
      // Manual XHR to track progress
      const xhr = new XMLHttpRequest();
      xhr.open('POST', '/api/upload', true);

      xhr.upload.onprogress = (e) => {
        if (e.lengthComputable) {
          const percent = Math.round((e.loaded / e.total) * 100);
          progressBar.style.width = `${percent}%`;
          progressLabel.textContent = `Uploading '${file.name}' (${percent}%)...`;
        }
      };

      xhr.onload = async () => {
        progressContainer.style.display = 'none';
        if (xhr.status === 200) {
          const result = JSON.parse(xhr.responseText);
          alert(`✓ Upload successful!\nIndexed ${result.num_chunks} chunks from ${result.num_pages} pages.`);
          await loadDocuments();
        } else {
          let message = xhr.statusText || 'Unknown error';
          try {
            const payload = JSON.parse(xhr.responseText);
            message = payload.detail || payload.error || message;
          } catch (error) {
            if (xhr.responseText) {
              message = xhr.responseText;
            }
          }
          alert(`Upload failed: ${message}`);
        }
      };

      xhr.onerror = () => {
        progressContainer.style.display = 'none';
        alert('Network error during file upload.');
      };

      xhr.send(formData);
    } catch (error) {
      progressContainer.style.display = 'none';
      console.error('Upload error:', error);
      alert('Upload failed.');
    }
  }

  // ─── Chat Logic ───
  chatForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    const query = chatInput.value.trim();
    if (!query) return;

    // Add user message
    addChatMessage('user', query);
    chatInput.value = '';
    
    // Add temporary thinking state
    const thinkingId = addChatMessage('assistant', 'Thinking...', true);

    try {
      const response = await fetch('/api/ask', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ question: query, n_results: 5 })
      });

      if (response.ok) {
        const result = await response.json();
        updateChatMessage(thinkingId, result.answer, result.sources);
      } else {
        updateChatMessage(thinkingId, 'Error generating response from backend.');
      }
    } catch (error) {
      console.error('Chat error:', error);
      updateChatMessage(thinkingId, 'Network error communicating with backend.');
    }
  });

  function addChatMessage(role, content, isThinking = false) {
    const id = Date.now().toString() + Math.random().toString(36).substring(2, 5);
    const msg = { id, role, content, sources: [], isThinking };
    chatHistory.push(msg);
    renderChat();
    return id;
  }

  function updateChatMessage(id, content, sources = []) {
    const msg = chatHistory.find(m => m.id === id);
    if (msg) {
      msg.content = content;
      msg.sources = sources;
      msg.isThinking = false;
      renderChat();
    }
  }

  function renderChat() {
    if (chatHistory.length === 0) {
      welcomeContainer.style.display = 'flex';
      chatContainer.style.display = 'none';
      btnClearChat.style.display = 'none';
      return;
    }

    welcomeContainer.style.display = 'none';
    chatContainer.style.display = 'flex';
    btnClearChat.style.display = 'block';

    chatContainer.innerHTML = '';
    chatHistory.forEach(msg => {
      const msgDiv = document.createElement('div');
      msgDiv.className = `chat-message ${msg.role}`;
      
      const textDiv = document.createElement('div');
      textDiv.className = 'message-text';
      textDiv.innerHTML = formatMarkdown(msg.content);
      msgDiv.appendChild(textDiv);

      if (msg.sources && msg.sources.length > 0) {
        const citationsDiv = document.createElement('div');
        citationsDiv.className = 'citations';
        
        const title = document.createElement('div');
        title.className = 'citations-title';
        title.textContent = 'Citations:';
        citationsDiv.appendChild(title);

        const listDiv = document.createElement('div');
        listDiv.className = 'citation-list';
        
        msg.sources.forEach(src => {
          const badge = document.createElement('span');
          badge.className = 'citation-badge';
          badge.textContent = `${src.source_filename} (p. ${src.page_num})`;
          badge.title = src.excerpt;
          listDiv.appendChild(badge);
        });

        citationsDiv.appendChild(listDiv);
        msgDiv.appendChild(citationsDiv);
      }

      chatContainer.appendChild(msgDiv);
    });

    // Scroll to bottom
    chatContainer.scrollTop = chatContainer.scrollHeight;
  }

  // Simple Markdown helper
  function formatMarkdown(text) {
    return text
      .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
      .replace(/\*(.*?)\*/g, '<em>$1</em>')
      .replace(/`(.*?)`/g, '<code>$1</code>')
      .replace(/\n/g, '<br>');
  }

  btnClearChat.addEventListener('click', () => {
    chatHistory = [];
    renderChat();
  });

  btnClearAll.addEventListener('click', clearAllDocuments);

  // Initial runs
  checkApiHealth();
  setInterval(checkApiHealth, 10000); // Pool every 10s
});
