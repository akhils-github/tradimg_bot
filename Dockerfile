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


# Expose the port the app runs on
EXPOSE 8000
# Run the bot
CMD ["python", "bot.py"]
