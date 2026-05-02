FROM python:3.11-slim

# Install system dependencies including locales
RUN apt-get update && apt-get install -y \
    locales \
    curl gnupg unzip git build-essential \
    gcc g++ python3-dev libsasl2-dev libpq-dev libssl-dev \
    libffi-dev libkrb5-dev libsasl2-modules-gssapi-mit \
    default-libmysqlclient-dev pkg-config \
    && rm -rf /var/lib/apt/lists/*

# Generate fr_FR.UTF-8 locale
RUN sed -i '/fr_FR.UTF-8/s/^# //g' /etc/locale.gen && locale-gen fr_FR.UTF-8

# Create a non-root user and switch to it
RUN useradd -m appuser && mkdir -p /app && chown appuser:appuser /app
USER appuser

WORKDIR /app

# Set environment variables for locale
ENV LANG=fr_FR.UTF-8
ENV LANGUAGE=fr_FR:fr
ENV LC_ALL=fr_FR.UTF-8

# Install Python dependencies
COPY --chown=appuser:appuser requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY --chown=appuser:appuser . .

# Set up entrypoint
COPY --chown=appuser:appuser start.sh /start.sh
RUN chmod +x /start.sh

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

EXPOSE 8000

CMD ["/start.sh"]
