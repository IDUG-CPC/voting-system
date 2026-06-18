FROM ubuntu:22.04

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    python3-dev \
    python3-setuptools \
    python3-pip \
    libsasl2-dev \
    libldap2-dev \
    libssl-dev \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Create app directory
WORKDIR /usr/src/moderator_app

# Copy app source
COPY . .

# Copy environment variables (optional, can be handled via docker-compose)


# Install Python dependencies
RUN pip3 install --no-cache-dir -r requirements.txt

RUN python3 manage.py collectstatic --noinput

# Expose internal port (can be anything — Traefik will route to it)
EXPOSE 9100

# Command is handled in docker-compose
