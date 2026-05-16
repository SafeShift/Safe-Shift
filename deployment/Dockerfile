FROM python:3.11-slim

WORKDIR /app

# Install system deps needed by opencv and mediapipe
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1 \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# TODO: replace with actual entry point once agent/orchestrator.py is implemented
CMD ["python", "-m", "agent.orchestrator"]
