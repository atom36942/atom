# Use official lightweight Python 3.11 base image
FROM python:3.11-slim

# Set working directory inside the container
WORKDIR /app

# Copy dependency requirements file first to leverage Docker cache
COPY requirements.txt .

# Install system-level dependencies for ODBC database connections and clean apt cache
RUN apt-get update && apt-get install -y unixodbc unixodbc-dev && rm -rf /var/lib/apt/lists/*

# Upgrade pip and install Python dependencies without caching packages
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application codebase into the container
COPY . .

# Document the port that the application listens on
EXPOSE 8000

# Specify the default command to launch the application
CMD ["python", "main.py"]