FROM python:latest

WORKDIR /app

# Copy requirements
COPY pyproject.toml /app/

# Install dependencies
RUN pip install --no-cache-dir \
    django \
    djangorestframework \
    psycopg2-binary \
    huey \
    redis \
    python-dotenv \
    pydantic \
    croniter \
    requests \
    django-allauth \
    minio \
    pillow \
    dj-database-url

# Copy application
COPY . /app/

# Create staticfiles directory
RUN mkdir -p /app/staticfiles

# Expose port
EXPOSE 8000

# Default command (override in docker-compose)
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]
