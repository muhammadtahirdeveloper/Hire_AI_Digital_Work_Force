# ============================================
# GmailMind — HireAI Digital Employee #1
# ============================================
FROM python:3.11-slim

# Prevent Python from writing .pyc files and enable unbuffered output
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Install system dependencies required by psycopg2 and other native libs
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        gcc \
        libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy package marker so Python recognises top-level modules
COPY __init__.py .

# Copy all application source packages
COPY agent/    ./agent/
COPY tools/    ./tools/
COPY memory/   ./memory/
COPY config/   ./config/
COPY scheduler/ ./scheduler/
COPY models/   ./models/
COPY api/          ./api/
COPY scripts/      ./scripts/
COPY orchestrator/ ./orchestrator/
COPY agents/       ./agents/
COPY skills/       ./skills/

# Expose the FastAPI port
EXPOSE 8000

# Default entry point — FastAPI server
CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]
