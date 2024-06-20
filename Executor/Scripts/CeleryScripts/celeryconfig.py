# celeryconfig.py
from celery.schedules import crontab

# Redis configuration
broker_url = "redis://localhost:6379/0"
result_backend = "redis://localhost:6379/0"

# Celery Beat Schedule
"""
Here we are using the crontab schedule to run the tasks at specific intervals.
The schedule is defined as a string in the format of "minute hour day_of_week month day_of_month".
This is the same format as used by the crontab command.
"""
beat_schedule = {
    "run_good_morning_scripts_every_day_at_830am": {
        "task": "V1_poetry_app.good_morning_scripts",
        "schedule": crontab(
            hour=18, minute=37, day_of_week="0-5"
        ),  # Monday to saturday
    },
    "run_amipy_every_day_at_9am": {
        "task": "V1_poetry_app.amipy",
        "schedule": crontab(hour=18, minute=39, day_of_week="0-4"),  # Monday to Friday
    },
    "run_expirytrader_every_day_at_916am": {
        "task": "V1_poetry_app.expiry_trader",
        "schedule": crontab(hour=18, minute=41, day_of_week="0-4"),  # Monday to Friday
    },
    "run_namaha_every_day_at_917am": {
        "task": "V1_poetry_app.namaha",
        "schedule": crontab(hour=9, minute=17, day_of_week="0-4"),  # Monday to Friday
    },
    "run_overnight_futures_exit_every_day_at_919am": {
        "task": "V1_poetry_app.overnight_exit",
        "schedule": crontab(hour=9, minute=19, day_of_week="1-4"),  # Tuesday to Friday
    },
    "run_pystocks_entry_every_day_at_920am": {
        "task": "V1_poetry_app.pystocks_entry",
        "schedule": crontab(hour=9, minute=35, day_of_week="0-4"),  # Monday to Friday
    },
    "run_pystocks_exit_every_day_at_935am": {
        "task": "V1_poetry_app.pystocks_exit",
        "schedule": crontab(hour=9, minute=35, day_of_week="0-4"),  # Monday to Friday
    },
    "run_golden_coin_every_day_at_942am": {
        "task": "V1_poetry_app.golden_coin",
        "schedule": crontab(hour=9, minute=42, day_of_week="0-4"),  # Monday to Friday
    },
    "run_om_every_day_at_943am": {
        "task": "V1_poetry_app.om",
        "schedule": crontab(hour=9, minute=43, day_of_week="0-4"),  # Monday to Friday
    },
    "run_mpwizard_every_day_at_10am": {
        "task": "V1_poetry_app.mpwizard",
        "schedule": crontab(hour=10, minute=0, day_of_week="0-4"),  # Monday to Friday
    },
    "run_sweep_orders_every_day_at_313pm": {
        "task": "V1_poetry_app.sweep_orders",
        "schedule": crontab(hour=15, minute=13, day_of_week="0-4"),  # Monday to Friday
    },
    "run_overnight_futures_entry_every_day_at_316pm": {
        "task": "V1_poetry_app.overnight_entry",
        "schedule": crontab(
            hour=15, minute=16, day_of_week="0-3"
        ),  # Monday to Thursday
    },
    "run_tradebook_validator_every_day_at_335pm": {
        "task": "V1_poetry_app.tradebook_validator",
        "schedule": crontab(hour=15, minute=35, day_of_week="0-4"),  # Monday to Friday
    },
    "run_eod_trade_db_logging_every_day_at_345pm": {
        "task": "V1_poetry_app.eod_trade_db_logging",
        "schedule": crontab(hour=15, minute=45, day_of_week="0-4"),  # Monday to Friday
    },
    "run_ticker_db_every_day_at_4pm": {
        "task": "V1_poetry_app.ticker_db",
        "schedule": crontab(hour=16, minute=00, day_of_week="0-4"),  # Monday to Friday
    },
    "run_eod_daily_reports_every_day_at_4pm": {
        "task": "V1_poetry_app.eod_daily_reports",
        "schedule": crontab(hour=16, minute=20, day_of_week="0-4"),  # Monday to Friday
    },
    "revoke_amipy_every_day_at_3_15pm": {
        "task": "V1_poetry_app.revoke_amipy_task",
        "schedule": crontab(hour=15, minute=30, day_of_week="0-4"),  # Monday to Friday
    },
    "revoke_mpwizard_every_day_at_3_16pm": {
        "task": "V1_poetry_app.revoke_mpwizard_task",
        "schedule": crontab(hour=15, minute=31, day_of_week="0-4"),  # Monday to Friday
    },
}

timezone = "Asia/Kolkata"  # Set your timezone to India
