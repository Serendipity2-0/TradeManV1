# Use the official Python image as the base
FROM python:3.10-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Set work directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Upgrade pip
RUN pip install --upgrade pip

# Copy only requirements to leverage Docker cache
COPY requirements.txt /app/

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the entire application code
COPY . /app/

# Make sure Python scripts are executable
RUN chmod +x Executor/Scripts/CeleryScripts/*.py Executor/Scripts/CeleryScripts/*.sh

# Set PYTHONPATH if needed
ENV PYTHONPATH=/app

# Set entrypoint
ENTRYPOINT ["/app/Executor/Scripts/CeleryScripts/entrypoint.sh"]
