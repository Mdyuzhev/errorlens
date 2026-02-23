# ErrorLens Full Stack Dockerfile
# Multi-stage: Vue frontend + Python backend

# Stage 1: Build Vue dashboard
FROM node:20-alpine AS frontend-builder

WORKDIR /build
COPY dashboard-vue/package*.json ./
RUN npm ci
COPY dashboard-vue/ ./

# For single-container mode, Vue is served by FastAPI at root
RUN npm run build

# Stage 2: Python backend with frontend assets
FROM python:3.11-slim

WORKDIR /app

# Install curl for healthcheck
RUN apt-get update && apt-get install -y curl && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY backend/app/ ./app/

# Copy Alembic for migrations
COPY backend/alembic.ini ./alembic.ini
COPY backend/alembic/ ./alembic/

# Copy built Vue dashboard from frontend stage
COPY --from=frontend-builder /build/dist/ ./dashboard-vue/dist/

# Copy bookmarklet scripts
COPY bookmarklet/recorder.js ./bookmarklet/recorder.js
COPY bookmarklet/recorder.min.js ./bookmarklet/recorder.min.js

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
