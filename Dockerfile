FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy backend requirements and install Python dependencies
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend application
COPY backend/app ./app
COPY allowed_domains.json blocked_domains.json ./

# Copy frontend files
COPY frontend/index.html ./static/

# Environment variables for production
ENV ENV=prod
ENV ALLOWED_ORIGINS="*"
ENV LOG_LEVEL=INFO

# Expose port
EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]