# Use an official Python runtime as a parent image
FROM python:3.12-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# Set the working directory in the container
WORKDIR /app

# Install system dependencies for Playwright
RUN apt-get update && apt-get install -y --no-install-recommends \
    wget \
    gnupg \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
# Copy only requirements first to leverage Docker cache
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip
RUN pip install --no-cache-dir -r requirements.txt

# Install Playwright browsers
RUN python -m playwright install --with-deps chromium

# Copy the rest of the application code
COPY . .

# Expose the port the app runs on (matching the uvicorn command)
# Cloud Run automatically uses the PORT environment variable, often 8080.
# Uvicorn will bind to 0.0.0.0 and the port specified.
# Let's stick to 8000 as configured in the potential __main__ block, but Cloud Run might override.
# Exposing it informs Docker, but Cloud Run manages the external mapping.
EXPOSE 8000

# Define the command to run the application
# Use the PORT environment variable provided by Cloud Run, default to 8000 if not set.
# Use sh -c to ensure shell variable expansion works.
CMD ["sh", "-c", "uvicorn server:app --host 0.0.0.0 --port ${PORT:-8000}"] 