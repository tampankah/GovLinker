FROM python:3.10-slim

# Set the working directory
WORKDIR /app

# Copy the requirements file and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Install system dependencies for Poppler
RUN apt-get update && apt-get install -y --no-install-recommends \
    poppler-utils \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Copy the application code
COPY . /app/

# Set environment variables
ENV UVICORN_CMD="uvicorn api.main:app --host 0.0.0.0 --port 8080 --reload"

# Expose the application port
EXPOSE 8080

# Run the application
CMD ["sh", "-c", "$UVICORN_CMD"]
