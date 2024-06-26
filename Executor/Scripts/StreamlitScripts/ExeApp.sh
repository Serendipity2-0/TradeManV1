#!/bin/bash

# Define maximum number of attempts
max_attempts=2

# Counter for the number of attempts
attempt=0

# Telegram bot parameters
telegram_bot_token='5994380365:AAFv0GSI78IxP6nI7g_xJPoqY3zWSfDHndQ'
chat_id='-367108102'
# Run the script
while true; do
    # Try to run the command
    ((attempt++))
    echo "Attempt: $attempt"
    
    # Source conda, activate the environment, and then run the streamlit app directly
    source /Users/traderscafe/miniconda3/etc/profile.d/conda.sh && \
    conda activate tradingenv && \
    cd /Users/traderscafe/Desktop/TradeManV1/  && \
    streamlit run Executor/ExecutorDashBoard/exe_main_app.py --server.port 8080 && \
    echo "Program started successfully" && break

    # If the command failed and we've reached the maximum number of attempts, send a message and exit
    if ((attempt==max_attempts)); then
        echo "The script ExeApp has some errors. Please Check !!!"
        
        # Send a message on Telegram
        curl -s -X POST https://api.telegram.org/bot$telegram_bot_token/sendMessage -d chat_id=$chat_id -d text="ExeApp errors. Please Check !!!"

        exit 1
    fi

    # Wait before retrying the command
    sleep 5
done
