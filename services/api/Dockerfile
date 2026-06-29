FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app/src

WORKDIR /app

COPY services/api/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

COPY services/api/src /app/src

EXPOSE 8000

CMD ["uvicorn", "emotion_talk_api.app:app", "--host", "0.0.0.0", "--port", "8000"]
