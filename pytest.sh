#!/usr/bin/bash

python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
pip install pytest pytest-cov

python3 -m smtpd -c DebuggingServer -n localhost:1025 &
redis-server &
celery -A monolith.background worker -l INFO -Q message --detach
rm -rf mmiab-test.db
pytest -s -v --cov monolith monolith/classes/tests --cov-report term-missing