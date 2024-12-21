# Use an official Python runtime as a parent image
FROM python:3.10-slim

# Set the working directory in the container
WORKDIR /app

# Copy the requirements file
COPY requirements/base.txt requirements/local.txt ./requirements/

# Install dependencies
RUN pip install --no-cache-dir -r requirements/local.txt

# Copy the application code
COPY . /app

# Expose the port the app runs on
EXPOSE 8000

# Command to run the app
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]