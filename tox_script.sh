python3 -m smtpd -c DebuggingServer -n localhost:1025 &
celery -A monolith.background  worker -l INFO -Q message --detach #for test send message by celery
rm -rf mmiab-test.db
pytest -s -v --cov monolith monolith/classes/tests --cov-report term-missing
#coveralls
