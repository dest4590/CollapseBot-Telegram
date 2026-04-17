FROM python:3.14-alpine

WORKDIR /app
ENV DOCKER_ENV=true

COPY requirements.txt .

RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt \
    && rm -rf /root/.cache

COPY . .

CMD ["python", "main.py"]
