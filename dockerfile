# Use official Python base image
FROM python:3.12-slim

# Set working directory inside container
WORKDIR /app

# Copy dependencies file first for caching
COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the app
COPY . .

# Expose port (if running a web app)
EXPOSE 5000

# Default command
CMD ["python", "app.py"]
