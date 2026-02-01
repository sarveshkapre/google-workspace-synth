FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt requirements-dev.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY src ./src

ENV GWSYNTH_DB_PATH=/app/data/gwsynth.db
RUN mkdir -p /app/data

EXPOSE 8000
CMD ["python", "-m", "gwsynth.main"]
