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
    libmagic1 \
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

# Create necessary directories
RUN mkdir -p /app/SampleData/Instruments \
    && mkdir -p /app/Data/AsmGsmList \
    && mkdir -p /app/Data/TradeManDB/UserTrades \
    && mkdir -p /app/Data/TradeManDB/Equity \
    && mkdir -p /app/Data/TradeManDB/Debt \
    && mkdir -p /app/Data/TradeManDB/Derivatives \
    && mkdir -p /app/Data/TradeManDB/Signals \
    && mkdir -p /app/Data/ErrorLogs \
    && mkdir -p /app/Data/ConsolidatedReports \
    && mkdir -p /app/Data/Logs \
    && mkdir -p /app/Executor/Scripts/CeleryScripts/logs \
    && mkdir -p /app/Data/FBJsonData \
    && mkdir -p /app/Executor/ExecutorUtils/ExeDBUtils/ExeFirebaseAdapter

# Create empty database files and logs (only if they don't exist)
RUN touch -a /app/Data/TradeManDB/Signals/signal_equity.db \
    && touch -a /app/Data/TradeManDB/Signals/signal_derivatives.db \
    && touch -a /app/Data/financial_data.db \
    && touch -a /app/Data/equity_stock_data.db \
    && touch -a /app/Data/stock_picks.db \
    && touch -a /app/Kaas_test.xlsx \
    && touch -a /app/Data/ErrorLogs/TradeManError.log \
    && touch -a /app/Data/ErrorLogs/ConsolidatedTradeManError.log \
    && touch -a /app/Data/Logs/params_log.csv

# Copy files
# COPY SampleData/Instruments/fno_info.csv /app/SampleData/Instruments/fno_info.csv
COPY Executor/ExecutorUtils/ExeDBUtils/ExeFirebaseAdapter/firebase_credentials.json /app/Executor/ExecutorUtils/ExeDBUtils/ExeFirebaseAdapter/

# Set permissions
RUN chmod -R 777 /app/Data /app/Executor/Scripts/CeleryScripts/logs /app/Executor/ExecutorUtils/ExeDBUtils/ExeFirebaseAdapter
