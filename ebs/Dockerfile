FROM docker.io/library/python:3.11-slim

ENV GUNICORN_CMD_ARGS="\
    --bind 0.0.0.0:5000 \
    --workers 4 \
    --access-logfile - \
    --preload"

WORKDIR /usr/src/app

COPY . /usr/src/app

RUN pip install --no-cache-dir .

USER 1001

CMD ["gunicorn", "verifiedfirst:create_app()"]
