# Use an official Python runtime as a parent image
FROM python:3.13-slim

# Set environment variables
ENV PYTHONUNBUFFERED True
ENV APP_HOME /app
ENV PORT 8080

# Create and set the working directory
WORKDIR $APP_HOME

# Install system dependencies (good practice, though may not be needed)
RUN apt-get update && apt-get install -y --no-install-recommends \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
# We copy *only* the requirements file first to leverage Docker cache
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Create a non-privileged user to run the app
RUN addgroup --system app && adduser --system --group app
USER app

# Copy the rest of the application code
# This includes server.py, the 'templates' folder, and the 'static' folder
COPY . .

# Expose the port the app runs on
EXPOSE $PORT

# Command to run the application using uvicorn
CMD ["uvicorn", "server:app", "--host", "0.0.0.0", "--port", "8080"]