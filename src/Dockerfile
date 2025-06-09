FROM python:3.10-slim

# Set working directory
WORKDIR /src

# Copy requirements file
COPY /cloud_run/requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY abracadabra /src/abracadabra
COPY cloud_run /src/cloud_run

# Set environment variables
ENV PORT=8080

# Run the application with Gunicorn
CMD exec gunicorn --bind :$PORT --workers 1 --threads 8 --timeout 0 cloud_run.main:app
