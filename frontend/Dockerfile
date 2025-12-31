FROM python:latest

WORKDIR /app

# Copy requirements
COPY pyproject.toml /app/

# Install dependencies
RUN pip install --no-cache-dir django django-htmx django-redis requests python-dotenv

# Copy application
COPY . /app/

# Create staticfiles directory
RUN mkdir -p /app/staticfiles

# Expose port
EXPOSE 3000

# Default command
CMD ["python", "manage.py", "runserver", "0.0.0.0:3000"]
