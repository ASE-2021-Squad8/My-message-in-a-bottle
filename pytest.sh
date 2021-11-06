#!/usr/bin/env bash

rm -rf mmiab-test.db
celery -A monolith.background worker -l INFO -Q message --detach #worker for the message queue
celery -A monolith.background worker -l INFO -Q notification --detach #worker for the email queue
pytest -s -v --cov monolith monolith/classes/tests --cov-report term-missing
