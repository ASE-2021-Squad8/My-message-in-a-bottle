#!/usr/bin/env bash

# $1 environment: DEV PROD
# $2 mail server
# $3 port
# $4 email address to send email
# $5 password
export FLASK_APP=monolith
if [[ $1 == "DEV" ]]
then
    export FLASK_ENV=development
    export FLASK_DEBUG=true
elif [[ $1 == "PROD" ]]
then
    export SMTP_SERVER=$2
    export MAIL_PORT=$3
    export MAIL_NOREPLY_ADDRESS=$4
    export MAIL_SERVER_PASSWORD=$5
fi

celery -A monolith.background worker -l INFO -Q message --detach # for sending messages 
celery -A monolith.background worker -l INFO -Q notification --detach # for sending email
celery -A monolith.background worker -l INFO --detach # for periodic tasks
celery -A monolith.background beat -l INFO --detach # for scheduling period task 

if [[ $1 == "DEV" ]]
then
    flask run
elif [[ $1 == "PROD" ]]
then
    waitress-serve --call 'monolith:create_app'
fi
