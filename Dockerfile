FROM python:3.11-slim

# Install system dependencies + Node.js
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    && curl -fsSL https://deb.nodesource.com/setup_18.x | bash - \
    && apt-get install -y nodejs \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy node dependencies
COPY package.json .
RUN npm install

# Copy application files
COPY . .

# Expose ports
EXPOSE 3000
EXPOSE 8000

# Start Node.js Web Server (which internally spawns the Python API)
CMD ["npm", "start"]
