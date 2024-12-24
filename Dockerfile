FROM python:3.10-slim

WORKDIR /app

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY . /app/

ENV UVICORN_CMD="uvicorn api.main:app --host 0.0.0.0 --port 8080 --reload"

EXPOSE 8080

CMD ["sh", "-c", "$UVICORN_CMD"]
