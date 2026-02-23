# Use official Python runtime as base image
FROM python:3.11-slim

# Disable Python stdout/stderr buffering so logs appear in real-time in Docker
ENV PYTHONUNBUFFERED=1

# Set working directory in container
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Explicitly ensure the DeepSeek supplemental instruction file is present
COPY deepseek_instruction.md ./deepseek_instruction.md

# Expose port for FastAPI
EXPOSE 8000

# Run the application
CMD ["python", "main.py"]
