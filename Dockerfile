# Railway production Dockerfile - bypasses Nixpacks nix-env failures
# Uses python:3.12-slim + Node 20 via apt for deterministic builds

FROM python:3.12-slim

# Install Node.js 20 + npm + curl for health checks
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    curl \
    ca-certificates \
    gnupg && \
    mkdir -p /etc/apt/keyrings && \
    curl -fsSL https://deb.nodesource.com/gpgkey/nodesource-repo.gpg.key | gpg --dearmor -o /etc/apt/keyrings/nodesource.gpg && \
    echo "deb [signed-by=/etc/apt/keyrings/nodesource.gpg] https://deb.nodesource.com/node_20.x nodistro main" | tee /etc/apt/sources.list.d/nodesource.list && \
    apt-get update && \
    apt-get install -y --no-install-recommends nodejs && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Verify installations
RUN python3 --version && node --version && npm --version

# Set working directory
WORKDIR /app

# Create Python virtual environment
RUN python3 -m venv /app/.venv

# Copy requirements first for layer caching
COPY requirements.txt /app/requirements.txt

# Install Python dependencies inside venv
RUN /app/.venv/bin/python -m pip install --upgrade pip setuptools wheel && \
    /app/.venv/bin/python -m pip install -r requirements.txt

# Copy entire repository
COPY . /app

# Build frontend if package.json exists (fail-closed)
RUN if [ -f frontend/package.json ]; then \
      cd frontend && \
      npm ci && \
      npm run build && \
      cd /app; \
    else \
      echo "WARNING: frontend/package.json not found - skipping frontend build"; \
    fi

# Set environment variables
ENV PATH="/app/.venv/bin:$PATH"
ENV NODE_ENV=production
ENV NEXT_TELEMETRY_DISABLED=1
ENV PYTHONUNBUFFERED=1

# Default command - run start.sh via bash
CMD ["bash", "start.sh"]
