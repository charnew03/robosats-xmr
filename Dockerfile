FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY backend ./backend
COPY pyproject.toml ./

ENV ROBOSATS_XMR_DB_PATH=/app/data/trades.db
ENV ROBOSATS_XMR_USE_FAKE_WALLET=true

EXPOSE 8000

CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
