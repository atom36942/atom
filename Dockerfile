# Use official lightweight Python 3.11 base image
FROM python:3.11-slim

# Set working directory inside the container
WORKDIR /app

# Copy dependency requirements file first to leverage Docker cache
COPY requirements.txt .

# Install system-level dependencies for ODBC database connections and Microsoft ODBC Driver for SQL Server
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl gnupg2 apt-transport-https ca-certificates unixodbc unixodbc-dev \
    && . /etc/os-release \
    && curl -fsSL -o /tmp/packages-microsoft-prod.deb "https://packages.microsoft.com/config/debian/${VERSION_ID}/packages-microsoft-prod.deb" \
    && dpkg -i /tmp/packages-microsoft-prod.deb \
    && rm /tmp/packages-microsoft-prod.deb \
    && apt-get update \
    && ACCEPT_EULA=Y apt-get install -y --no-install-recommends msodbcsql17 msodbcsql18 \
    && rm -rf /var/lib/apt/lists/*

# Upgrade pip and install Python dependencies without caching packages
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application codebase into the container
COPY . .

# Document the port that the application listens on
EXPOSE 8000

# Specify the default command to launch the application
CMD ["python", "main.py"]