# celeryconfig.py
from celery.schedules import crontab

# Redis configuration
broker_url = "redis://127.0.0.1:6379/0"
result_backend = "redis://127.0.0.1:6379/0"

# Celery Beat Schedule
"""
Here we are using the crontab schedule to run the tasks at specific intervals.
The schedule is defined as a string in the format of "minute hour day_of_week month day_of_month".
This is the same format as used by the crontab command.
"""
beat_schedule = {
    "run_good_morning_scripts_every_day_at_830am": {
        "task": "Executor.Scripts.CeleryScripts.V1_poetry_app.good_morning_scripts",
        "schedule": crontab(hour=8, minute=30, day_of_week="1-6"),  # Monday to saturday
    },
    "run_fast_api_server_every_day_at_001am": {
        "task": "Executor.Scripts.CeleryScripts.V1_poetry_app.fast_api_server",
        "schedule": crontab(hour=0, minute=1, day_of_week="*"),  # every day
    },
    "run_equity_entry_every_day_at_930am": {
        "task": "Executor.Scripts.CeleryScripts.V1_poetry_app.equity_entry",
        "schedule": crontab(hour=9, minute=30, day_of_week="1-5"),  # Monday to Friday
    },
    "run_equity_stoploss_every_day_at_935am": {
        "task": "Executor.Scripts.CeleryScripts.V1_poetry_app.equity_exit",
        "schedule": crontab(hour=9, minute=35, day_of_week="1-5"),  # Monday to Friday
    },
    "run_golden_coin_every_day_at_1000am": {
        "task": "Executor.Scripts.CeleryScripts.V1_poetry_app.golden_coin",
        "schedule": crontab(hour=10, minute=0, day_of_week="1-5"),  # Monday to Friday
    },
    "run_sweep_orders_every_day_at_313pm": {
        "task": "Executor.Scripts.CeleryScripts.V1_poetry_app.sweep_orders",
        "schedule": crontab(hour=15, minute=13, day_of_week="1-5"),  # Monday to Friday
    },
    "run_tradebook_validator_every_day_at_335pm": {
        "task": "Executor.Scripts.CeleryScripts.V1_poetry_app.tradebook_validator",
        "schedule": crontab(hour=15, minute=35, day_of_week="1-5"),  # Monday to Friday
    },
    "run_eod_trade_db_logging_every_day_at_345pm": {
        "task": "Executor.Scripts.CeleryScripts.V1_poetry_app.eod_trade_db_logging",
        "schedule": crontab(hour=15, minute=45, day_of_week="1-5"),  # Monday to Friday
    },
    "run_ticker_db_every_day_at_4pm": {
        "task": "Executor.Scripts.CeleryScripts.V1_poetry_app.ticker_db",
        "schedule": crontab(hour=16, minute=00, day_of_week="1-5"),  # Monday to Friday
    },
    "run_eod_daily_reports_every_day_at_4pm": {
        "task": "Executor.Scripts.CeleryScripts.V1_poetry_app.eod_daily_reports",
        "schedule": crontab(hour=16, minute=20, day_of_week="1-5"),  # Monday to Friday
    },
}

# Add these configuration options
beat_max_loop_interval = 5  # Check the schedule every 5 seconds
beat_sync_every = 0  # Disable beat state persistence

# Ignore missed tasks on startup
beat_scheduler = "redbeat.RedBeatScheduler"
redbeat_redis_url = "redis://127.0.0.1:6379/1"
redbeat_lock_key = None

timezone = "Asia/Kolkata"  # Set your timezone to India

# Add this new configuration option
broker_connection_retry_on_startup = True
