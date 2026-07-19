FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y build-essential && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy dependencies and install
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Expose Streamlit port for Hugging Face Spaces
EXPOSE 7860

# Streamlit starts the FastAPI backend internally
CMD ["streamlit", "run", "app.py", "--server.port=7860", "--server.address=0.0.0.0"]
