FROM python:3.11-slim

# ffmpeg for the final render; libsndfile for soundfile/librosa.
RUN apt-get update \
    && apt-get install -y --no-install-recommends ffmpeg libsndfile1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt requirements-ml.txt ./
RUN pip install --no-cache-dir -r requirements.txt -r requirements-ml.txt

COPY app ./app
COPY alembic ./alembic
COPY alembic.ini ./

ENV STORAGE_DIR=/data/projects \
    DATABASE_URL=sqlite:////data/localmv.db
VOLUME ["/data"]
EXPOSE 8000

# Apply migrations, then serve.
CMD ["sh", "-c", "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8000"]
