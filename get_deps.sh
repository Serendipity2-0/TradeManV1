#!/usr/bin/env bash


cd /app
source trademan.env
workers=6
gunicorn User.UserApi.main --workers $workers -k uvicorn.workers.UvicornWorker --timeout 1800  --worker-class uvicorn.workers.UvicornWorker  --access-logfile - --error-logfile - --log-level debug --bind 0.0.0.0:8000