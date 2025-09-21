# Use a modern Python base image
FROM python:3.12-slim

# Disable pip cache to reduce image size
ENV PIP_NO_CACHE_DIR=1

# Install system dependencies (git required for Pyrogram)
RUN apt-get update && \
    apt-get install -y git build-essential && \
    rm -rf /var/lib/apt/lists/*

# Upgrade pip and setuptools
RUN pip3 install --upgrade pip setuptools

# Copy application code
COPY . /app/
WORKDIR /app/

# Install Python dependencies
RUN pip3 install --no-cache-dir -U -r requirements.txt

# Run the bot
CMD ["python3", "-m", "TEAMZYRO"]
