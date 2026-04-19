FROM python:3.11-slim
WORKDIR /app
RUN pip install --no-cache-dir requests
COPY sync.py .
CMD ["python", "-u", "sync.py"]
