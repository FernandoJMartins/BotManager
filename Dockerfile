FROM python:3.9-slim

# Set the working directory
WORKDIR /app

# Copy the requirements file
COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the application code
COPY src/ ./src/
COPY . .

# Expose the port the app runs on
EXPOSE 5000

# Set PYTHONPATH to ensure proper module imports
ENV PYTHONPATH=/app

# Command to run the application
CMD ["python", "-m", "src.app"]