# Build in local: docker build . --platform linux/arm64 -t rsstranslator/rsstranslator:dev
# Run with docker-compose to test: docker-compose -f docker-compose.test.yml up -d
# Push to dev: docker push rsstranslator/rsstranslator:dev
# Run with docker-compose in dev: docker-compose -f docker-compose.dev.yml up -d
# Multi-arch build:
# docker buildx create --use
# docker buildx build . --platform linux/arm64,linux/amd64 --push -t rsstranslator/rsstranslator:latest -t rsstranslator/rsstranslator:version

FROM python:3.11-slim AS builder

ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 0
ENV DockerHOME=/home/rsstranslator
RUN mkdir -p $DockerHOME/data
WORKDIR $DockerHOME
COPY . $DockerHOME
#RUN pip config set global.index-url http://127.0.0.1:8000/simple
RUN pip install -r requirements/dev.txt --no-cache-dir -U && \
    python manage.py init_server && \
    find $DockerHOME -type d -name "__pycache__" -exec rm -r {} + && \
    rm -rf $DockerHOME/.cache/pip \
EXPOSE 8000
CMD python manage.py init_server && python manage.py run_huey & uvicorn config.asgi:application --host 0.0.0.0
