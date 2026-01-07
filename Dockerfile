FROM python:3.11-slim

WORKDIR /app

ARG GIT_COMMIT
ENV GIT_HASH=${GIT_COMMIT:-unknown}

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Директория для данных (если нужна)
RUN mkdir -p /app/data

# Команда запуска бота
CMD ["python", "bot.py"]
