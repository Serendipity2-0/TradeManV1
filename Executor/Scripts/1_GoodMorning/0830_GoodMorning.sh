#!/bin/bash

# Path to your .env file
env_file="/Users/omkar/Desktop/TradeManV1/trademan.env"

# Load the variables from the .env file
if [ -f "$env_file" ]; then
    export $(cat $env_file | xargs)
else
    echo "Environment file $env_file not found"
    exit 1
fi

# Define maximum number of attempts
max_attempts=5

# Counter for the number of attempts
attempt=0

# Telegram bot parameters
telegram_bot_token='YOUR_TELEGRAM_BOT_TOKEN'
chat_id='YOUR_CHAT_ID'

# Run the script
while true; do
    # Try to run the command
    ((attempt++))
    echo "Attempt: $attempt"
    
    # Source conda, activate the environment and run the script
    source /Users/amolkittur/miniconda3/etc/profile.d/conda.sh && \
    conda activate $CONDA_ENV && \
    cd $START_DIR && \
    /Users/amolkittur/miniconda3/envs/$CONDA_ENV/bin/python Executor/Scripts/1_GoodMorning/1_Login/DailyLogin.py && \
    /Users/amolkittur/miniconda3/envs/$CONDA_ENV/bin/python Executor/Scripts/1_GoodMorning/2_FundsValidator/FundValidator.py && \
    /Users/amolkittur/miniconda3/envs/$CONDA_ENV/bin/python Executor/Scripts/1_GoodMorning/3_MarketInfoUpdate/MarketInfoUpdate.py && \
    /Users/amolkittur/miniconda3/envs/$CONDA_ENV/bin/python Executor/Scripts/1_GoodMorning/4_DailyInstrumentAggregator/DailyInstrumentAggregator.py && \
    /Users/amolkittur/miniconda3/envs/$CONDA_ENV/bin/python Executor/Scripts/1_GoodMorning/5_TelegramOrderBot/TelegramOrderBot.py && \
    echo "Program started successfully" && break

    # If the command failed and we've reached the maximum number of attempts, send a message and exit
    if ((attempt==max_attempts)); then
        echo "Can't Login!!!"
        
        # Send a message on Telegram
        curl -s -X POST https://api.telegram.org/bot$telegram_bot_token/sendMessage -d chat_id=$chat_id -d text="Can't Login. Please Check !!!"

        exit 1
    fi

    # Wait before retrying the command
    sleep 5
done
