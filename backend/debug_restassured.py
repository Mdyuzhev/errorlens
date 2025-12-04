"""Debug script to test REST Assured generation with sample data."""

import json
from app.restassured_generator import generate_restassured_file, generate_pom_xml
from app.models_pydantic import RecordedHttpExchange, RecordedRequest, RecordedResponse

# Sample recorded requests based on the pytest test session
sample_requests = [
    RecordedHttpExchange(
        id=1,
        timestamp="2025-12-04T10:00:00Z",
        request=RecordedRequest(
            timestamp="2025-12-04T10:00:00Z",
            method="POST",
            url="https://api.wh-lab.ru/api/auth/login",
            headers={"Content-Type": "application/json"},
            body=json.dumps({"username": "ivanov", "password": "password123"}),
            content_type="application/json"
        ),
        response=RecordedResponse(
            status=200,
            status_text="OK",
            headers={"Content-Type": "application/json"},
            body=json.dumps({"token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."}),
            duration_ms=150
        )
    ),
    RecordedHttpExchange(
        id=2,
        timestamp="2025-12-04T10:00:01Z",
        request=RecordedRequest(
            timestamp="2025-12-04T10:00:01Z",
            method="GET",
            url="https://api.wh-lab.ru/api/products",
            headers={"Authorization": "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."},
            body=None,
            content_type=None
        ),
        response=RecordedResponse(
            status=200,
            status_text="OK",
            headers={"Content-Type": "application/json"},
            body=json.dumps([{"id": 1, "name": "Product 1", "price": 100}]),
            duration_ms=80
        )
    ),
    RecordedHttpExchange(
        id=3,
        timestamp="2025-12-04T10:00:02Z",
        request=RecordedRequest(
            timestamp="2025-12-04T10:00:02Z",
            method="POST",
            url="https://api.wh-lab.ru/api/products",
            headers={
                "Content-Type": "application/json",
                "Authorization": "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
            },
            body=json.dumps({
                "name": "Тест",
                "quantity": 1,
                "price": 12,
                "description": "Тест",
                "category": "Одежда"
            }),
            content_type="application/json"
        ),
        response=RecordedResponse(
            status=201,
            status_text="Created",
            headers={"Content-Type": "application/json"},
            body=json.dumps({"id": 42, "name": "Тест", "quantity": 1, "price": 12}),
            duration_ms=120
        )
    ),
    RecordedHttpExchange(
        id=4,
        timestamp="2025-12-04T10:00:03Z",
        request=RecordedRequest(
            timestamp="2025-12-04T10:00:03Z",
            method="GET",
            url="https://api.wh-lab.ru/api/products",
            headers={"Authorization": "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."},
            body=None,
            content_type=None
        ),
        response=RecordedResponse(
            status=200,
            status_text="OK",
            headers={"Content-Type": "application/json"},
            body=json.dumps([
                {"id": 1, "name": "Product 1", "price": 100},
                {"id": 42, "name": "Тест", "price": 12}
            ]),
            duration_ms=75
        )
    ),
]


if __name__ == "__main__":
    print("=" * 70)
    print("Generating REST Assured test file...")
    print("=" * 70)

    java_code = generate_restassured_file(
        recorded_requests=sample_requests,
        class_name="WhLabApiTest",
        package_name="com.errorlens.tests"
    )

    print("\n" + java_code)

    print("\n" + "=" * 70)
    print("pom.xml preview (first 30 lines):")
    print("=" * 70)

    pom = generate_pom_xml()
    for line in pom.split('\n')[:30]:
        print(line)

    print("\n... (truncated)")

    # Save to files for inspection
    with open("debug_output/WhLabApiTest.java", "w", encoding="utf-8") as f:
        f.write(java_code)

    with open("debug_output/pom.xml", "w", encoding="utf-8") as f:
        f.write(pom)

    print("\n" + "=" * 70)
    print("Files saved to debug_output/")
    print("=" * 70)
