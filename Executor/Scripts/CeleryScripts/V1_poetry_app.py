# celery_app.py
from celery import Celery
import subprocess
from datetime import datetime
import requests
from time import sleep
import redis
import logging
from logging import FileHandler
import sys, os
from dotenv import load_dotenv

# Define constants and load environment variables
DIR = os.getcwd()
sys.path.append(DIR)  # Add the current directory to the system path

ENV_PATH = os.path.join(DIR, "trademan.env")
load_dotenv(ENV_PATH)

CONDA_PATH = os.getenv("CONDA_PATH")
CONDA_ENV_NAME = os.getenv("CONDA_ENV_NAME")
PROJECT_PATH = os.getenv("PROJECT_PATH")
PYTHON_ENV_PATH = os.getenv("PYTHON_ENV_PATH")

# Create a Celery instance
app = Celery("tasks")
app.config_from_object("Executor.Scripts.CeleryScripts.celeryconfig")

# redis client
redis_client = redis.StrictRedis(host="localhost", port=6379, db=0)

# Telegram bot parameters
TELEGRAM_BOT_TOKEN = os.getenv("ERROR_TELEGRAM_BOT_TOKEN")
CHAT_ID = os.getenv("ERROR_CHAT_ID")

# log files path
log_dir = os.getenv("CELERY_SCRIPTS_LOG_PATH")

# Strategy Constants
AMIPY = "amipy"
OVERNIGHT_FUTURES = "overnight_futures"
EXPIRY_TRADER = "expiry_trader"
NAMAHA = "namaha"
MPWIZARD = "mpwizard"
GOLDEN_COIN = "golden_coin"
OM = "om"
PYSTOCKS = "pystocks"


def setup_logger(name, log_file, level=logging.DEBUG):  # Set level to DEBUG
    handler = FileHandler(log_file)
    handler.setLevel(level)
    formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
    handler.setFormatter(formatter)

    logger = logging.getLogger(name)
    logger.setLevel(level)
    if not logger.handlers:
        logger.addHandler(handler)
    logger.debug(f"Logger {name} setup at {log_file} with level {level}")
    return logger


# Redirect print statements to the logger
class LoggerWriter:
    def __init__(self, logger, level):
        self.logger = logger
        self.level = level

    def write(self, message):
        if message.strip() != "":
            self.logger.log(self.level, message.strip())

    def flush(self):
        pass


# Function to run the script
def run_script(script_path, retry_hour, logger):
    """
    This is the replacement for the old sh files.
    In this function, we are running the script and handling the retry logic.
    This function is called by the celery task.
    This function stores the output of the files in a log file.
    """
    max_attempts = 1
    attempt = 0

    logger.debug("Redirecting stdout and stderr to logger")
    sys.stdout = LoggerWriter(logger, logging.INFO)
    sys.stderr = LoggerWriter(logger, logging.ERROR)

    while True:
        current_hour = datetime.now().hour
        if current_hour >= retry_hour:
            logger.info("The script will not retry after retry_hour.")
            return "The script will not retry after retry_hour."

        attempt += 1
        logger.info(f"Attempt: {attempt}")

        try:
            logger.debug(f"Running script {script_path}")
            with subprocess.Popen(
                f"source {CONDA_PATH}/etc/profile.d/conda.sh && "
                f"conda activate {CONDA_ENV_NAME} && "
                f"cd {PROJECT_PATH} && "
                f"{PYTHON_ENV_PATH} {script_path}",
                shell=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                executable="/bin/bash",
                bufsize=1,
                universal_newlines=True,
            ) as process:
                for stdout_line in iter(process.stdout.readline, ""):
                    logger.info(stdout_line.strip())
                for stderr_line in iter(process.stderr.readline, ""):
                    logger.error(stderr_line.strip())
                process.stdout.close()
                process.stderr.close()
                return_code = process.wait()
                if return_code:
                    logger.error(
                        f"Script {script_path} failed with return code {return_code}"
                    )
                    return "failed"
                logger.info(f"Program {script_path} completed successfully")
                return "success"
        except subprocess.CalledProcessError as e:
            logger.error(f"Error running script {script_path}: {e}")
            if attempt == max_attempts:
                current_hour = datetime.now().hour
                if current_hour <= retry_hour:
                    logger.error(
                        f"The script {script_path} has some errors. Please Check !!!"
                    )
                    message = f"{script_path} errors. Please Check !!!"
                    requests.post(
                        f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage",
                        data={"chat_id": CHAT_ID, "text": message},
                    )
                    return "failed"
                else:
                    logger.error(
                        f"Script {script_path} failed after retry_hour, exiting without notification."
                    )
                    return "failed after retry_hour"

        sleep(5)


def run_multiple_scripts(script_paths, logger):
    # here we are running a set of scripts and logging the output in a log file
    for script_path in script_paths:
        result = run_script(script_path, 20, logger)
        if "failed" in result:
            return result
    return "All scripts executed successfully."


# Below are the celery tasks/cronjobs


@app.task
def good_morning_scripts():
    good_morning_logger = setup_logger(
        "good_morning_logger", f"{log_dir}/good_morning.log"
    )
    scripts = [
        "Executor/Scripts/1_GoodMorning/1_Login/DailyLogin.py",
        "Executor/Scripts/1_GoodMorning/2_FundsValidator/FundValidator.py",
        "Executor/Scripts/1_GoodMorning/3_MarketInfoUpdate/MarketInfoUpdate.py",
        "Executor/Scripts/1_GoodMorning/4_DailyInstrumentAggregator/DailyInstrumentAggregator.py",
        "Executor/Scripts/1_GoodMorning/5_TelegramOrderBot/TelegramOrderBot.py",
    ]
    return run_multiple_scripts(scripts, good_morning_logger)


@app.task(bind=True)
def amipy(self):
    amipy_logger = setup_logger(AMIPY, f"{log_dir}/{AMIPY}.log")
    task_id = self.request.id
    redis_client.set("amipy_task_id", task_id)
    return run_script(
        "Executor/NSEStrategies/Derivatives/AmiPy/AmiPyLive.py", 15, amipy_logger
    )


@app.task
def overnight_exit():
    overnight_futures_logger = setup_logger(
        OVERNIGHT_FUTURES, f"{log_dir}/{OVERNIGHT_FUTURES}.log"
    )
    return run_script(
        "Executor/NSEStrategies/Derivatives/OvernightFutures/Screenipy_futures_morning.py",
        10,
        overnight_futures_logger,
    )


@app.task
def expiry_trader():
    expirytrader_logger = setup_logger(EXPIRY_TRADER, f"{log_dir}/{EXPIRY_TRADER}.log")
    return run_script(
        "Executor/NSEStrategies/Derivatives/ExpiryTrader/ExpiryTrader.py",
        15,
        expirytrader_logger,
    )


@app.task
def namaha():
    namaha_logger = setup_logger(NAMAHA, f"{log_dir}/{NAMAHA}.log")
    return run_script(
        "Executor/NSEStrategies/Derivatives/Namaha/Namaha.py", 15, namaha_logger
    )


@app.task
def pystocks_entry():
    pystocks_logger = setup_logger(PYSTOCKS, f"{log_dir}/{PYSTOCKS}.log")
    return run_script(
        "Executor/NSEStrategies/Derivatives/PyStocks/PyStocksMain.py",
        15,
        pystocks_logger,
    )


@app.task
def pystocks_exit():
    pystocks_logger = setup_logger(PYSTOCKS, f"{log_dir}/{PYSTOCKS}.log")
    return run_script(
        "Executor/NSEStrategies/Derivatives/PyStocks/PyStocksStoploss.py",
        15,
        pystocks_logger,
    )


@app.task
def golden_coin():
    golden_coin_logger = setup_logger(GOLDEN_COIN, f"{log_dir}/{GOLDEN_COIN}.log")
    return run_script(
        "Executor/NSEStrategies/Derivatives/GoldenCoin/GoldenCoin.py",
        15,
        golden_coin_logger,
    )


@app.task
def om():
    om_logger = setup_logger(OM, f"{log_dir}/{OM}.log")
    return run_script("Executor/NSEStrategies/Derivatives/Om/Om.py", 15, om_logger)


@app.task(bind=True)
def mpwizard(self):
    mpwizard_logger = setup_logger(MPWIZARD, f"{log_dir}/{MPWIZARD}.log")
    task_id = self.request.id
    redis_client.set("mpwizard_task_id", task_id)
    return run_script(
        "Executor/NSEStrategies/Derivatives/MPWizard/MPWizard.py", 15, mpwizard_logger
    )


@app.task
def sweep_orders():
    sweep_orders_logger = setup_logger("sweep_orders", f"{log_dir}/sweep_orders.log")
    return run_script(
        "Executor/Scripts/2_GoodEvening/1_SweepOrders/SweepOrders.py",
        16,
        sweep_orders_logger,
    )


@app.task
def overnight_entry():
    overnight_futures_logger = setup_logger(
        OVERNIGHT_FUTURES, f"{log_dir}/{OVERNIGHT_FUTURES}.log"
    )
    return run_script(
        "Executor/NSEStrategies/Derivatives/OvernightFutures/Screenipy_futures_afternoon.py",
        16,
        overnight_futures_logger,
    )


@app.task
def tradebook_validator():
    tradebook_validator_logger = setup_logger(
        "tradebook_validator", f"{log_dir}/tradebook_validator.log"
    )
    return run_script(
        "Executor/Scripts/2_GoodEvening/2_DailyTradeBookValidator/TradeBookValidator.py",
        16,
        tradebook_validator_logger,
    )


@app.task
def eod_trade_db_logging():
    eod_trade_db_logging_logger = setup_logger(
        "eod_trade_db_logging", f"{log_dir}/eod_trade_db_logging.log"
    )
    return run_script(
        "Executor/Scripts/2_GoodEvening/3_EODTradeDBLogging/EODDBLog.py",
        17,
        eod_trade_db_logging_logger,
    )


@app.task
def eod_daily_reports():
    eod_daily_reports_logger = setup_logger(
        "eod_daily_reports", f"{log_dir}/eod_daily_reports.log"
    )
    return run_script(
        "Executor/Scripts/2_GoodEvening/4_EODDailyReports/EODReports.py",
        17,
        eod_daily_reports_logger,
    )


@app.task
def ticker_db():
    ticker_db_logger = setup_logger("ticker_db", f"{log_dir}/ticker_db.log")
    return run_script(
        "Executor/Scripts/2_GoodEvening/5_TickerDB/TickerDB.py", 17, ticker_db_logger
    )


@app.task
def revoke_amipy_task():
    task_id = redis_client.get("amipy_task_id")
    if task_id:
        app.control.revoke(task_id.decode("utf-8"), terminate=True)
        message = f"Task {task_id.decode('utf-8')} has been revoked."
        requests.post(
            f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage",
            data={"chat_id": CHAT_ID, "text": message},
        )
        return message
    return "No task_id found to revoke."


@app.task
def revoke_mpwizard_task():
    task_id = redis_client.get("mpwizard_task_id")
    if task_id:
        app.control.revoke(task_id.decode("utf-8"), terminate=True)
        message = f"Task {task_id.decode('utf-8')} has been revoked."
        requests.post(
            f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage",
            data={"chat_id": CHAT_ID, "text": message},
        )
        return message
    return "No task_id found to revoke."


def start_worker():
    from celery.bin import worker

    worker_instance = worker.worker(app=app)
    worker_instance.run(loglevel="info", traceback=True)


def start_beat():
    from celery.bin import beat

    beat = beat.beat(app=app)
    beat.run(loglevel="info")
