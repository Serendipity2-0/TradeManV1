#!/usr/bin/env bash

source trademan.env
workers=6
gunicorn User.UserApi.main:app_fastapi --workers $workers -k uvicorn.workers.UvicornWorker --timeout 1800  --worker-class uvicorn.workers.UvicornWorker  --access-logfile - --error-logfile - --log-level debug --bind 0.0.0.0:8000