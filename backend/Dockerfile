FROM python:latest

WORKDIR /app

# Copy requirements
COPY pyproject.toml /app/

# Install dependencies from pyproject.toml
RUN pip install --no-cache-dir -e .

# Copy application
COPY . /app/

# Create staticfiles directory
RUN mkdir -p /app/staticfiles

# Expose port
EXPOSE 8000

# Default command (override in docker-compose)
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]
