# ErrorLens Full Stack Dockerfile for Railway
# Multi-stage build: Vue frontend + Python backend

# Stage 1: Build Vue dashboard
FROM node:20-alpine AS frontend-builder

WORKDIR /build

# Copy package files and install dependencies
COPY dashboard-vue/package*.json ./
RUN npm ci

# Copy source and build
COPY dashboard-vue/ ./
RUN npm run build

# Stage 2: Python backend with frontend assets
FROM python:3.11-slim

WORKDIR /app

# Install curl for healthcheck + Java & Maven for REST Assured tests
RUN apt-get update && apt-get install -y \
    curl \
    default-jdk \
    maven \
    && rm -rf /var/lib/apt/lists/*

# Set JAVA_HOME
ENV JAVA_HOME=/usr/lib/jvm/default-java
ENV PATH="${JAVA_HOME}/bin:${PATH}"

# Install Python dependencies
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY backend/app/ ./app/

# Copy Alembic for migrations
COPY backend/alembic.ini ./alembic.ini
COPY backend/alembic/ ./alembic/

# Create data directory for SQLite (if no PostgreSQL configured)
RUN mkdir -p /app/data

# Copy built Vue dashboard from frontend stage
COPY --from=frontend-builder /build/dist/ ./dashboard-vue/dist/

# Copy bookmarklet scripts
COPY bookmarklet/ ./bookmarklet/

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Run with uvicorn
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
