# Build in local: docker build . --platform linux/arm64 -t rsstranslator/rsstranslator:dev
# run with docker-compose to test: docker-compose up -d
# Push:
# Multi-arch build:
# docker buildx create --use
# docker buildx build . --platform linux/arm64,linux/amd64 --push -t rsstranslator/rsstranslator:latest -t rsstranslator/rsstranslator:version

FROM python:3.11-slim AS builder

ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1
ENV DockerHOME=/home/rsstranslator
RUN mkdir -p $DockerHOME/data
WORKDIR $DockerHOME
COPY . $DockerHOME
RUN pip install -r requirements/prod.txt --no-cache-dir
EXPOSE 8000
CMD python manage.py collectstatic --no-input && \
    python manage.py makemigrations && \
    python manage.py migrate && \
    python manage.py create_default_superuser && \
    python manage.py run_huey & \
    uvicorn config.asgi:application --host 0.0.0.0