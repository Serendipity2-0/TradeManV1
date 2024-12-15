#!/bin/bash

# Source conda configuration
source ~/miniconda3/etc/profile.d/conda.sh

# Define maximum number of attempts
max_attempts=1

# Counter for the number of attempts
attempt=0

# Run the script
while true; do
    # Check if the current hour is greater than 16 (4 pm)
    current_hour=$(date +%H)
    if ((current_hour >= 23)); then
        echo "The script will not retry after 11 pm."
        break
    fi

    # Try to run the command
    ((attempt++))
    echo "Attempt: $attempt"
    
    # Change directory, activate conda environment and run the script
    cd /Users/omkar/Desktop/TradeManV1 && \
    conda activate macenv && \
    python Executor/NSEStrategies/Derivatives/GoldenCoin/GoldenCoin.py && \
    echo "Program started successfully" && break

    # Break if max attempts reached
    if ((attempt >= max_attempts)); then
        echo "Maximum attempts reached. Exiting."
        break
    fi
done
