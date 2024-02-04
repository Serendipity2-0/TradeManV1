#!/bin/bash

# Define maximum number of attempts
max_attempts=5

# Counter for the number of attempts
attempt=0

# Telegram bot parameters
telegram_bot_token='5994380365:AAFv0GSI78IxP6nI7g_xJPoqY3zWSfDHndQ'
chat_id='-367108102'

#TODO: Take the path from the environment variable
# Run the script
while true; do
    # Try to run the command
    ((attempt++))
    echo "Attempt: $attempt"
    
    # Source conda, activate the environment and run the script
    source /Users/amolkittur/miniconda3/etc/profile.d/conda.sh && \
	conda activate traderscafe && \
    cd /Users/amolkittur/Desktop/TradeManV1/ && \
	/Users/amolkittur/miniconda3/envs/traderscafe/bin/python Executor/Scripts/1_GoodMorning/1_Login/DailyLogin.py && \
    /Users/amolkittur/miniconda3/envs/traderscafe/bin/python Executor/Scripts/1_GoodMorning/2_FundsValidator/FundValidator.py && \
    /Users/amolkittur/miniconda3/envs/traderscafe/bin/python Executor/Scripts/1_GoodMorning/3_MarketInfoUpdate/MarketInfoUpdate.py && \
    /Users/amolkittur/miniconda3/envs/traderscafe/bin/python Executor/Scripts/1_GoodMorning/4_DailyInstrumentAggregator/DailyInstrumentAggregator.py && \
    /Users/amolkittur/miniconda3/envs/traderscafe/bin/python Executor/Scripts/1_GoodMorning/5_TelegramOrderBot/TelegramOrderBot.py && \
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