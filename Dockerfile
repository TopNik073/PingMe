FROM python:3.12-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    netcat-traditional \
    && rm -rf /var/lib/apt/lists/*

# Install dependencies for psycopg2
RUN apt-get update && apt-get install -y \
    libpq-dev \
    gcc \
    python3-dev

# Create logs directory with proper permissions
RUN mkdir -p /app/logs && chmod 777 /app/logs

# Copy the requirements file
COPY requirements.txt .

# Install dependencies
RUN pip install --upgrade pip
RUN pip install -r requirements.txt

# Copy the source code
COPY . .

# Run migrations and start the application
CMD while ! nc -z db 5432; do sleep 0.1; done && \
    alembic upgrade head && \
    uvicorn main:app --host 0.0.0.0 --port 8000 