"""Sample session data for testing generators.

This fixture represents a typical API session:
1. Login (POST /auth/login) -> get token
2. Get products list (GET /products)
3. Create product (POST /products)
4. Verify creation (GET /products)
"""

import json

# Sample recorded requests matching real-world API flow
SAMPLE_REQUESTS_RAW = [
    {
        "id": 1,
        "timestamp": "2025-12-04T10:00:00Z",
        "request": {
            "timestamp": "2025-12-04T10:00:00Z",
            "method": "POST",
            "url": "https://api.wh-lab.ru/api/auth/login",
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps({"username": "ivanov", "password": "password123"}),
            "content_type": "application/json",
        },
        "response": {
            "status": 200,
            "status_text": "OK",
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps({"token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.test"}),
            "duration_ms": 150,
        },
    },
    {
        "id": 2,
        "timestamp": "2025-12-04T10:00:01Z",
        "request": {
            "timestamp": "2025-12-04T10:00:01Z",
            "method": "GET",
            "url": "https://api.wh-lab.ru/api/products",
            "headers": {"Authorization": "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.test"},
            "body": None,
            "content_type": None,
        },
        "response": {
            "status": 200,
            "status_text": "OK",
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps([{"id": 1, "name": "Product 1", "price": 100}]),
            "duration_ms": 80,
        },
    },
    {
        "id": 3,
        "timestamp": "2025-12-04T10:00:02Z",
        "request": {
            "timestamp": "2025-12-04T10:00:02Z",
            "method": "POST",
            "url": "https://api.wh-lab.ru/api/products",
            "headers": {
                "Content-Type": "application/json",
                "Authorization": "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.test",
            },
            "body": json.dumps(
                {
                    "name": "Тестовый товар",
                    "quantity": 1,
                    "price": 12,
                    "description": "Описание товара",
                    "category": "Одежда",
                }
            ),
            "content_type": "application/json",
        },
        "response": {
            "status": 201,
            "status_text": "Created",
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps({"id": 42, "name": "Тестовый товар", "quantity": 1, "price": 12}),
            "duration_ms": 120,
        },
    },
    {
        "id": 4,
        "timestamp": "2025-12-04T10:00:03Z",
        "request": {
            "timestamp": "2025-12-04T10:00:03Z",
            "method": "GET",
            "url": "https://api.wh-lab.ru/api/products",
            "headers": {"Authorization": "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.test"},
            "body": None,
            "content_type": None,
        },
        "response": {
            "status": 200,
            "status_text": "OK",
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps(
                [
                    {"id": 1, "name": "Product 1", "price": 100},
                    {"id": 42, "name": "Тестовый товар", "price": 12},
                ]
            ),
            "duration_ms": 75,
        },
    },
]


def get_sample_exchanges():
    """Get sample data as RecordedHttpExchange objects."""
    from app.models_pydantic import RecordedHttpExchange

    return [RecordedHttpExchange(**req) for req in SAMPLE_REQUESTS_RAW]


def get_sample_raw():
    """Get sample data as raw dicts (as stored in DB)."""
    return SAMPLE_REQUESTS_RAW
