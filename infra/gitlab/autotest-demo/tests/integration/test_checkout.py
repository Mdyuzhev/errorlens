import allure
import pytest

pytestmark = [
    allure.feature("Checkout"),
    allure.epic("E2E"),
]


class TestCheckout:
    """End-to-end checkout flow tests."""

    @allure.severity(allure.severity_level.BLOCKER)
    @pytest.mark.regression
    def test_full_checkout_flow(self, http_session, base_url):
        """Multi-step checkout: cart → coupon → shipping → order → confirm."""
        with allure.step("Add item to cart"):
            r = http_session.post(f"{base_url}/post", json={"item": "laptop", "qty": 1})
            assert r.status_code == 200

        with allure.step("Apply coupon"):
            r = http_session.post(f"{base_url}/post", json={"coupon": "SAVE10"})
            assert r.status_code == 200

        with allure.step("Fill shipping info"):
            r = http_session.post(f"{base_url}/post", json={
                "address": "123 Test St", "city": "Moscow",
            })
            assert r.status_code == 200

        with allure.step("Submit order"):
            r = http_session.post(f"{base_url}/post", json={"action": "submit"})
            assert r.status_code == 200

        with allure.step("Verify confirmation"):
            r = http_session.get(f"{base_url}/get", params={"order": "confirmed"})
            assert r.status_code == 200
            assert r.json()["args"]["order"] == "confirmed"

    @allure.severity(allure.severity_level.BLOCKER)
    @pytest.mark.regression
    def test_checkout_with_invalid_card(self, http_session, base_url):
        """Intentionally failing: expects validation error but gets 200."""
        response = http_session.post(f"{base_url}/post", json={
            "card": "0000-0000-0000-0000",
        })
        assert response.status_code == 422, (
            f"Expected validation error, got {response.status_code}"
        )

    @allure.severity(allure.severity_level.NORMAL)
    @pytest.mark.smoke
    def test_checkout_empty_cart(self, http_session, base_url):
        """Empty cart returns 4xx error."""
        response = http_session.get(f"{base_url}/status/400")
        assert response.status_code == 400
