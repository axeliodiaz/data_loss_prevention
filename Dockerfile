FROM python:3.10-slim

# Set the working directory
WORKDIR /app

# Install dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    netcat-openbsd \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*


# Copy the requirements files
COPY requirements/base.txt requirements/local.txt /app/requirements/

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements/local.txt

# Copy the rest of the application
COPY . .

# Wait for the database and run the server
CMD ["sh", "-c", "python manage.py wait_for_db && python manage.py runserver 0.0.0.0:8000"]