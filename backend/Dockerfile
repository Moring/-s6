FROM python:latest

WORKDIR /app

# Copy requirements
COPY pyproject.toml /app/

# Install system packages needed (tmux, neovim, psql)
RUN apt-get update \
	 && apt-get install -y --no-install-recommends \
		 curl \
		 unzip \
		 tmux \
		 sqlite3 \
		 postgresql-client \
		 jq \
		 less \
		 neovim \
	 && rm -rf /var/lib/apt/lists/*

# Install Python dependencies from pyproject.toml
RUN pip install --no-cache-dir -e .

# Copy application
COPY . /app/

# Create staticfiles directory
RUN mkdir -p /app/staticfiles

# Expose port
EXPOSE 8000

# Default command (override in docker-compose)
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]
