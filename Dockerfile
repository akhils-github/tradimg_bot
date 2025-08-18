# Use an official Python runtime as a parent image
FROM python:3.10-slim

# Create a non-root user
ARG UID=1000
RUN adduser --disabled-password --gecos '' --uid "${UID}" appuser

# Set the working directory in the container
WORKDIR /app

# Copy the requirements file into the container at /app
COPY requirements.txt .

# Change to the non-root user before installing packages
USER appuser

# Install any needed packages specified in requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application's source code into the container
COPY . .

# Expose the port the app runs on
EXPOSE 8000

# Define the command to run the application
CMD ["python", "bot.py"]