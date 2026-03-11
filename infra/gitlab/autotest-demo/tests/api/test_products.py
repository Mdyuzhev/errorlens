import struct

import allure

pytestmark = [allure.feature("Product Catalog")]

# Minimal valid 1x1 PNG (67 bytes)
_MINIMAL_PNG = (
    b"\x89PNG\r\n\x1a\n"  # signature
    + struct.pack(">I", 13) + b"IHDR" + struct.pack(">IIBBBBB", 1, 1, 8, 2, 0, 0, 0)
    + b"\x90wS\xde"  # IHDR CRC
    + struct.pack(">I", 12) + b"IDAT"
    + b"\x08\xd7ch\x00\x00\x00\x82\x00\x81"  # compressed pixel
    + b"\xa0\xd4\xe2&"  # IDAT CRC
    + struct.pack(">I", 0) + b"IEND" + b"\xaeB`\x82"  # IEND
)


class TestProducts:
    """Product catalog API tests."""

    @allure.story("Product list")
    @allure.severity(allure.severity_level.NORMAL)
    def test_get_product_list(self, http_session, base_url):
        """GET product list returns JSON."""
        response = http_session.get(f"{base_url}/json")
        assert response.status_code == 200
        assert "application/json" in response.headers.get("Content-Type", "")

        allure.attach(
            _MINIMAL_PNG,
            name="Response screenshot",
            attachment_type=allure.attachment_type.PNG,
        )

    @allure.story("Product search")
    @allure.severity(allure.severity_level.NORMAL)
    def test_product_search_by_name(self, http_session, base_url):
        """Search products by name via query params."""
        with allure.step("Build query"):
            params = {"q": "laptop", "category": "electronics"}

        with allure.step("Execute search"):
            response = http_session.get(f"{base_url}/get", params=params)

        with allure.step("Parse results"):
            assert response.status_code == 200
            assert response.json()["args"]["q"] == "laptop"

    @allure.story("Product stock")
    @allure.severity(allure.severity_level.MINOR)
    def test_product_out_of_stock(self, http_session, base_url):
        """Intentionally failing: stock count mismatch."""
        response = http_session.get(f"{base_url}/get", params={"stock": 5})
        assert response.status_code == 200
        stock = int(response.json()["args"]["stock"])
        assert stock == 0, f"Product stock count mismatch: expected 0, got {stock}"

    @allure.story("Product images")
    @allure.severity(allure.severity_level.NORMAL)
    def test_product_image_upload(self, http_session, base_url, tmp_path):
        """Upload product image via POST."""
        image_file = tmp_path / "product.txt"
        image_file.write_text("fake image content for upload test")

        with open(image_file, "rb") as f:
            response = http_session.post(
                f"{base_url}/post",
                files={"file": ("product.txt", f, "text/plain")},
                headers={},  # let requests set multipart headers
            )

        assert response.status_code == 200
        allure.attach(
            image_file.read_text(),
            name="Uploaded file content",
            attachment_type=allure.attachment_type.TEXT,
        )
