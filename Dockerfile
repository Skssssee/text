FROM python:3.8.5-slim-buster

ENV PIP_NO_CACHE_DIR 1

# Upgrade pip and setuptools
RUN pip3 install --upgrade pip setuptools

# Copy application code
COPY . /app/

# Set working directory
WORKDIR /app/

# Install Python dependencies
RUN pip3 install --no-cache-dir -U -r requirements.txt

# Run the bot
CMD ["python3", "-m", "TEAMZYRO"]
