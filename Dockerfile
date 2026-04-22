FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt ./
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 5685

CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port ${API_PORT:-5685}"]
