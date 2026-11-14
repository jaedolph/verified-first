FROM registry.access.redhat.com/hi/python:3.14

ENV GUNICORN_CMD_ARGS="\
    --bind 0.0.0.0:5000 \
    --workers 4 \
    --access-logfile - \
    --preload"

USER 0
RUN ["python3", "-m", "venv", "/opt/venv"]
ENV PATH="/opt/venv/bin:$PATH"

WORKDIR /usr/src/app

COPY . .

RUN ["pip3", "install", "--no-cache-dir", "-r", "requirements.txt", "."]

USER 1001

CMD ["gunicorn", "verifiedfirst:create_app()"]
