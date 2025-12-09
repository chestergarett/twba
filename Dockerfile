# Use slim Python image
FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy app code
COPY . .

# Cloud Run uses $PORT automatically
ENV PORT=8050

EXPOSE 8050

# Run your Dash app (edit if your main file is different)
CMD ["python", "app.py"]
