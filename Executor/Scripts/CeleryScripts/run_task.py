#!/usr/bin/env python3
"""
Script to run individual Celery tasks.
"""
import os
import sys
from argparse import ArgumentParser

# Add project root to Python path
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
sys.path.insert(0, project_root)

from Executor.Scripts.CeleryScripts.V1_poetry_app import (
    good_morning_scripts,
    fast_api_server,
    amipy,
    equity_entry,
    equity_exit,
    mpwizard,
    golden_coin,
    sweep_orders,
    tradebook_validator,
    eod_trade_db_logging,
    eod_daily_reports,
    ticker_db,
)

# Map of task names to task functions
TASKS = {
    'good_morning_scripts': good_morning_scripts,
    'fast_api_server': fast_api_server,
    'amipy': amipy,
    'equity_entry': equity_entry,
    'equity_exit': equity_exit,
    'mpwizard': mpwizard,
    'golden_coin': golden_coin,
    'sweep_orders': sweep_orders,
    'tradebook_validator': tradebook_validator,
    'eod_trade_db_logging': eod_trade_db_logging,
    'eod_daily_reports': eod_daily_reports,
    'ticker_db': ticker_db,
}

def main():
    parser = ArgumentParser(description='Run a Celery task')
    parser.add_argument('task_name', choices=list(TASKS.keys()), help='Name of the task to run')
    args = parser.parse_args()

    if args.task_name not in TASKS:
        print(f"Error: Unknown task '{args.task_name}'")
        print(f"Available tasks: {', '.join(TASKS.keys())}")
        sys.exit(1)

    print(f"Starting task: {args.task_name}")
    task = TASKS[args.task_name]
    result = task.delay()
    print(f"Task {args.task_name} started with ID: {result.id}")

if __name__ == '__main__':
    main()
