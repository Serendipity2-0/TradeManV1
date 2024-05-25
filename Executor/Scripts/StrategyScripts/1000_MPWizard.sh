#!/bin/bash

# Define maximum number of attempts
max_attempts=1

# Counter for the number of attempts
attempt=0

# Telegram bot parameters
telegram_bot_token='5994380365:AAFv0GSI78IxP6nI7g_xJPoqY3zWSfDHndQ'
chat_id='-367108102'

# Run the script
while true; do
    # Check if the current hour is greater than 14 (2 pm)
    current_hour=$(date +%H)
    if ((current_hour >= 14)); then
        echo "The script will not retry after 3 pm."
        break
    fi

    # Try to run the command
    ((attempt++))
    echo "Attempt: $attempt"
    
    # Source conda, activate the environment and run the script
    source /Users/traderscafe/miniconda3/etc/profile.d/conda.sh && \
    conda activate tradingenv && \
    cd /Users/traderscafe/Desktop/TradeManV1/ && \
    /Users/traderscafe/miniconda3/envs/tradingenv/bin/python Executor/Strategies/MPWizard/MPWizard.py && \
    echo "Program started successfully" && break

    if ((attempt==max_attempts)); then
        # Get the current time
        current_hour=$(date +%H)
        if ((current_hour<=15)); then
            echo "The script MPWizard has some errors. Please Check !!!"
            
            # Send a message on Telegram
            curl -s -X POST https://api.telegram.org/bot$telegram_bot_token/sendMessage -d chat_id=$chat_id -d text="MPWizard errors. Please Check !!!"

            exit 1
        else
            # Exit without a message if the time is greater than 15
            echo "Script failed after 3 PM, exiting without notification."
            exit 1
        fi
    fi

    # Wait before retrying the command
    sleep 5
done
