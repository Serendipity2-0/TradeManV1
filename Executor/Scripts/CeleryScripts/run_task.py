# run_all_tasks.py
from Executor.Scripts.CeleryScripts.V1_poetry_app import *

# Using this function we are running the celery tasks

# Trigger the tasks
results = []
results.append(good_morning_scripts.delay())
results.append(amipy.delay())
results.append(overnight_exit.delay())
results.append(expiry_trader.delay())
results.append(namaha.delay())
results.append(pystocks_entry.delay())
results.append(pystocks_exit.delay())
results.append(golden_coin.delay())
results.append(om.delay())
results.append(mpwizard.delay())
results.append(sweep_orders.delay())
results.append(overnight_entry.delay())
results.append(tradebook_validator.delay())
results.append(eod_trade_db_logging.delay())
results.append(eod_daily_reports.delay())
results.append(ticker_db.delay())
