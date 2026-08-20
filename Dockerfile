# This tells Render exactly how to build and run your app:
# install ffmpeg (needed for video processing), install Python packages,
# then start the web server.

FROM python:3.11-slim

# Install ffmpeg (this is the part shared hosting could never do)
RUN apt-get update && \
    apt-get install -y --no-install-recommends ffmpeg && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python dependencies first (Docker caches this layer so rebuilds
# are faster when you only change app code, not requirements)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the project in
COPY . .

# Make sure the folders the app writes to actually exist
RUN mkdir -p output temp

# Render sets the PORT environment variable automatically — the app must
# listen on that port. gunicorn is a production-grade server (the Flask
# dev server used by `python app.py` isn't meant for real traffic).
CMD gunicorn --bind 0.0.0.0:$PORT --timeout 120 app:app
