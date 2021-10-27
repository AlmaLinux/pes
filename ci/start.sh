#! /usr/bin/env sh
set -e

# If there's a prestart.sh script in the /src/app directory, run it before starting
PRE_START_PATH="/src/app/prestart.sh"
echo "Checking for script in $PRE_START_PATH"
if [ -f $PRE_START_PATH ] ; then
    echo "Running script $PRE_START_PATH"
    . $PRE_START_PATH
else
    echo "There is no script $PRE_START_PATH"
fi

# start uWSGI
exec gunicorn -w "${UWSGI_PROCESSES:-2}" -b "${UWSGI_ADDRESS}:${UWSGI_PORT}" --config /src/app/wsgi.ini.py main:app
