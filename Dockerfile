FROM python:3.14-alpine

COPY requirements.txt requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY . /app

WORKDIR /app
ENV DOCKER_ENV=true

CMD ["python", "main.py"]
