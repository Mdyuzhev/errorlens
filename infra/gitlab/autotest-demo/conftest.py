import os
import random
import time

import pytest
import requests
from faker import Faker


@pytest.fixture(scope="session")
def base_url():
    """Base URL of the application under test."""
    return os.environ.get("APP_URL", "https://httpbin.org")


@pytest.fixture(scope="session")
def faker_ru():
    """Faker instance with Russian locale."""
    return Faker("ru_RU")


@pytest.fixture
def http_session(base_url):
    """Requests session with base headers."""
    session = requests.Session()
    session.headers.update({
        "Accept": "application/json",
        "Content-Type": "application/json",
        "X-Test-Client": "errorlens-autotest",
    })
    session.base_url = base_url
    yield session
    session.close()


@pytest.fixture(autouse=True)
def random_delay():
    """Occasionally adds random delay to simulate instability (30% chance)."""
    if random.random() < 0.3:
        time.sleep(random.uniform(0.1, 0.5))
