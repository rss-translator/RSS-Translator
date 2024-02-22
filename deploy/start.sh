#!/bin/sh
# Don't run this script directly, use 'systemctl start rsstranslator' instead.
if ! command -v .venv/bin/python > /dev/null; then
        echo "Python is not installed."
        exit 1
    fi
if ! command -v .venv/bin/uvicorn > /dev/null; then
    echo "Uvicorn is not installed."
    exit 1
fi

{
.venv/bin/python manage.py run_huey &
.venv/bin/uvicorn config.asgi:application --host 0.0.0.0 &
}
wait