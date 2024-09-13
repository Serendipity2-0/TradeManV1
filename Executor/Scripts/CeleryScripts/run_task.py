# run_all_tasks.py
from Executor.Scripts.CeleryScripts.V1_poetry_app import *

# Using this function we are running the celery tasks

# Trigger the tasks
results = []
results.append(good_morning_scripts.delay())
results.append(fast_api_server.delay())
results.append(amipy.delay())
results.append(equity_entry.delay())
results.append(equity_exit.delay())
results.append(mpwizard.delay())
results.append(golden_coin.delay())
results.append(sweep_orders.delay())
results.append(tradebook_validator.delay())
results.append(eod_trade_db_logging.delay())
results.append(eod_daily_reports.delay())
results.append(ticker_db.delay())
