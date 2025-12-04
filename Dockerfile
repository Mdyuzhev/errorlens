# ErrorLens Full Stack Dockerfile for Railway
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

# Copy Vue dashboard dist for static serving
COPY dashboard-vue/dist/ ./dashboard-vue/dist/

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Run with uvicorn
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
