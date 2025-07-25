FROM python:3.12-alpine

COPY requirements.txt requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY . /app

WORKDIR /app

RUN mkdir -p /app/config && \
    echo "[settings]" > /app/config/config.ini && \
    echo "translation_enabled = true" >> /app/config/config.ini

CMD ["python", "main.py"]
