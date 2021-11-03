#!/usr/bin/env bash

rm -rf mmiab-test.db 
celery -A monolith.background  worker -l INFO -Q message --detach #woker for the message queue
celery -A monolith.background  worker -l INFO -Q notification --detach #woker for the email queue
pytest -s --cov-config .coveragerc --cov monolith monolith/classes/tests
