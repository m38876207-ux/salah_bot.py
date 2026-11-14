FROM python:3.12-slim

# The bot only needs Python 3.11+; slim keeps the image small (~150 MB).
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PORT=8080

WORKDIR /app

# Install dependencies first so Docker can cache this layer.
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copy the project.
COPY . .

# $PORT enables the tiny HTTP health endpoint used by Fly/Render/Northflank.
CMD ["python", "main.py"]
