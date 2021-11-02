python3 -m smtpd -c DebuggingServer -n localhost:1025 &
celery -A monolith.background  worker -l INFO -Q message --detach #for test send message by celery
rm -rf mmiab-test.db
pytest --cov-config .coveragerc --cov monolith monolith/classes/tests -s
#coveralls