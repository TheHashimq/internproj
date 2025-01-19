# Use the official Python 3.9 slim image
FROM python:3.9-slim

# Set environment variables
ENV PYTHONUNBUFFERED 1
ENV FLASK_APP app.py

# Install system dependencies (ping and traceroute)
RUN apt-get update && apt-get install -y \
    traceroute \
    iputils-ping \
    && rm -rf /var/lib/apt/lists/*

# Set the working directory in the container
WORKDIR /app

# Copy the current directory contents into the container at /app
COPY . /app/

# Install the Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Expose the port the app will run on
EXPOSE 5000

# Use Gunicorn as the web server for production
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "app:app"]

