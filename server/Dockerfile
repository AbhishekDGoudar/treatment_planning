FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    unzip \
    curl \
    libmagic1 \
    && rm -rf /var/lib/apt/lists/*

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Set working directory
WORKDIR /app

# Copy project files
COPY . .

# Unzip data (Requirement 1a)
# Assuming data.zip is in the server root
RUN if [ -f data.zip ]; then unzip data.zip -d .; fi

# Install dependencies and sync environment (Requirement 1b)
# This creates the .venv and adds it to the PATH
RUN uv sync --frozen
ENV PATH="/app/.venv/bin:$PATH"

# Expose port
EXPOSE 8000

# Run migrations and start server (Requirement 1c, 1d)
CMD ["sh", "-c", "python manage.py makemigrations && python manage.py migrate && python manage.py runserver 0.0.0.0:8000"]