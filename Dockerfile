# Use official Python image
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Copy requirements first to leverage Docker cache
COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the bot code into the container
COPY . .

# Ensure the .env file is in the container (OR mount it during run)
# If you don't want to COPY it (for security), you can mount it using a volume during docker run
# COPY .env .  ← (Uncomment if you want to copy it in)

# Run the bot
CMD ["python", "bot.py"]
