#!/usr/bin/bash

python3.9 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
pip install pytest pytest-cov

python3.9 -m smtpd -c DebuggingServer -n localhost:1025 &
PYTHON_PID=$!
redis-server &
REDIS_PID=$!
celery -A monolith.background worker -l INFO -Q message --detach
CELERY_PID=$!
rm -rf mmiab-test.db
pytest -s -v --cov monolith monolith/classes/tests
kill -9 $PYTHON_PID
kill -9 $REDIS_PID
kill -9 $CELERY_PID
