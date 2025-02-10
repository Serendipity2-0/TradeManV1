# Celery Task Management System

This Celery application manages various automated trading tasks including market data collection, trade execution, and reporting.

## Prerequisites

- Python 3.7+
- Redis server running locally (port 6379)
- Conda environment with required dependencies
- Environment variables set in `trademan.env`

## Environment Variables Required

The following environment variables must be set in `trademan.env`:

```
CONDA_PATH=<path to conda installation>
CONDA_ENV_NAME=<name of conda environment>
PROJECT_PATH=<path to project root>
PYTHON_ENV_PATH=<path to python interpreter>
ERROR_TELEGRAM_BOT_TOKEN=<telegram bot token for error notifications>
ERROR_CHAT_ID=<telegram chat id for notifications>
CELERY_SCRIPTS_LOG_PATH=<path for celery script logs>
```

## Available Tasks

### Morning Tasks
- `good_morning_scripts`: Executes a sequence of morning initialization scripts
  - Daily Login
  - Daily Instrument Aggregator
  - Daily Equity Calculations
  - ASM/GSM Aggregator

### Trading Tasks
- `amipy`: Runs the AmiPy trading strategy
- `equity_entry`: Handles equity entry positions
- `equity_exit`: Manages equity exit positions
- `mpwizard`: Executes the MPWizard trading strategy
- `golden_coin`: Runs the Golden Coin trading strategy

### Evening Tasks
- `sweep_orders`: Cleans up pending orders
- `tradebook_validator`: Validates the day's tradebook
- `eod_trade_db_logging`: Logs end-of-day trade data
- `eod_daily_reports`: Generates daily reports
- `ticker_db`: Updates ticker database

### Server Tasks
- `fast_api_server`: Runs the FastAPI server
- `clear_celery_tasks`: Clears all Celery tasks from Redis

### Control Tasks
- `revoke_amipy_task`: Stops the AmiPy strategy
- `revoke_mpwizard_task`: Stops the MPWizard strategy

## Running with Docker

The application is containerized using Docker and can be run using Docker Compose. This setup includes:
- Redis server
- FastAPI application
- Celery worker
- Celery beat scheduler

### Prerequisites

1. Install Docker and Docker Compose
2. Ensure trademan.env file exists with required environment variables

### Running the Application

1. Build and start all services:
```bash
docker-compose up --build
```

2. Start in detached mode (background):
```bash
docker-compose up -d
```

3. View logs:
```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f fastapi
docker-compose logs -f celery_worker
docker-compose logs -f celery_beat
docker-compose logs -f redis
```

### Managing Services

- Stop all services:
```bash
docker-compose down
```

- Restart a specific service:
```bash
docker-compose restart fastapi
docker-compose restart celery_worker
docker-compose restart celery_beat
```

- Scale celery workers:
```bash
docker-compose up -d --scale celery_worker=3
```

### Accessing Services

- FastAPI: http://localhost:8082
- Redis: localhost:6379
- Swagger UI: http://localhost:8082/swagger

### Troubleshooting

1. Check service status:
```bash
docker-compose ps
```

2. Check service logs:
```bash
docker-compose logs -f [service_name]
```

3. Rebuild services after changes:
```bash
docker-compose up --build -d
```

4. Reset everything:
```bash
docker-compose down -v
docker-compose up --build
```

### Manual Running (Alternative)

## Running Individual Tasks

Tasks can be executed using the `run_task.py` script. The script must be run from the project root directory:

```bash
cd /Users/omkar/Desktop/TradeManV1  # Change to project root
python Executor/Scripts/CeleryScripts/run_task.py <task_name>
```

Available tasks:
- good_morning_scripts
- fast_api_server
- amipy
- equity_entry
- equity_exit
- mpwizard
- golden_coin
- sweep_orders
- tradebook_validator
- eod_trade_db_logging
- eod_daily_reports
- ticker_db

Example:
```bash
python Executor/Scripts/CeleryScripts/run_task.py good_morning_scripts
```

### Troubleshooting Task Execution

1. ModuleNotFoundError: No module named 'Executor'
   - Make sure you're running the script from the project root directory
   - Verify your Python environment has all required dependencies installed
   - Check that PYTHONPATH includes the project root directory

2. Redis Connection Error
   - Ensure Redis server is running: `redis-cli ping` should return "PONG"
   - Check Redis connection settings in celeryconfig.py
   - Verify Redis service is active: `launchctl list | grep redis`

3. Task Not Found Error
   - Use one of the task names listed above
   - Task names are case-sensitive
   - Run with --help to see available tasks: `python Executor/Scripts/CeleryScripts/run_task.py --help`

## Logging

All tasks write detailed logs to the directory specified in `CELERY_SCRIPTS_LOG_PATH`. Each task has its own log file with the following information:
- Timestamp
- Log level (DEBUG/INFO/ERROR)
- File name and line number
- Detailed message

Log files are automatically created in the specified directory with the task name as the file name (e.g., `good_morning.log`, `amipy.log`).

## Error Handling

- Tasks will retry until their specified retry hour
- Failures are logged and notified via Telegram
- After retry hour, tasks will exit without retrying
- Task status can be monitored through logs and Redis

## Maintenance

To clear all running tasks:
```bash
python Executor/Scripts/CeleryScripts/clear_tasks.py
```

## Best Practices

1. Always check logs after task execution
2. Monitor Redis for task status
3. Use appropriate retry hours for different tasks
4. Keep environment variables updated
5. Regularly clear completed tasks from Redis

## Configured Schedules

The following tasks are scheduled in `celeryconfig.py`:

### Morning Tasks
- Good Morning Scripts: 2:45 PM IST (Monday to Saturday)
- Equity Entry: 9:30 AM IST (Monday to Friday)
- Equity Exit: 9:35 AM IST (Monday to Friday)
- Golden Coin: 10:00 AM IST (Monday to Friday)

### Evening Tasks
- Sweep Orders: 3:13 PM IST (Monday to Friday)
- Tradebook Validator: 3:35 PM IST (Monday to Friday)
- EOD Trade DB Logging: 3:45 PM IST (Monday to Friday)
- Ticker DB: 4:00 PM IST (Monday to Friday)
- EOD Daily Reports: 4:20 PM IST (Monday to Friday)

### Continuous Tasks
- FastAPI Server: 12:01 AM IST (Every day)

Note: All times are in Indian Standard Time (IST). The scheduler uses the Asia/Kolkata timezone as configured in `celeryconfig.py`.
