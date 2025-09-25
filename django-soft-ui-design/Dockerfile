# Use official Python image as base
FROM python:3.9-slim

# Set environment variables to prevent Python from writing .pyc files and buffering output
ENV PYTHONUNBUFFERED 1

# Set the working directory inside the container
WORKDIR /app

# Install dependencies
COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

# Copy the project code into the container
COPY . /app/

# Expose the port on which the Django app will run
EXPOSE 8000

# Set the entry point for the container to run Django with Gunicorn
CMD ["gunicorn", "myproject.wsgi:application", "--bind", "0.0.0.0:8000"]
