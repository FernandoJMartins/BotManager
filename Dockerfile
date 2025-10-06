FROM python:3.9-slim

# Set the working directory
WORKDIR /app

# Copy the requirements file
COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the application code
COPY src/ ./src/

# Copy the environment variables file from src/env to container root as .env
COPY src/env .env

# Expose the port the app runs on
EXPOSE 5000

# Command to run the application
CMD ["python", "-m", "src.app"]
