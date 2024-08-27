FROM python:3.11-slim

# Set environment variables
ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED 1
ENV TZ=Asia/Kolkata

# Install dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    git \
    libmagic1 \
    libffi-dev \
    libssl-dev \
    libxml2-dev \
    libxslt1-dev \
    python3-dev \
    python3-pip \
    python3-venv \
    tzdata \
    && rm -rf /var/lib/apt/lists/*


# set working directory
WORKDIR /app

# Copy the requirements file and key to the container
COPY requirements.txt .

RUN pip3 install --upgrade setuptools && \
    pip3 install wheel && \
    pip3 install --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code to the container
COPY . .

RUN chmod +x ./get_deps.sh
CMD ["./get_deps.sh"]