import struct

import errorlens as el


@el.feature("Product Catalog")
class TestProducts:
    """Product catalog API tests."""

    @el.story("Product list")
    @el.severity("normal")
    def test_get_product_list(self, http_session, base_url):
        """GET product list returns JSON."""
        response = http_session.get(f"{base_url}/json")
        assert response.status_code == 200
        assert "application/json" in response.headers.get("Content-Type", "")

    @el.story("Product search")
    @el.severity("normal")
    def test_product_search_by_name(self, http_session, base_url):
        """Search products by name via query params."""
        with el.step("Build query"):
            params = {"q": "laptop", "category": "electronics"}

        with el.step("Execute search"):
            response = http_session.get(f"{base_url}/get", params=params)

        with el.step("Parse results"):
            assert response.status_code == 200
            assert response.json()["args"]["q"] == "laptop"

    @el.story("Product stock")
    @el.severity("minor")
    def test_product_out_of_stock(self, http_session, base_url):
        """Intentionally failing: stock count mismatch."""
        response = http_session.get(f"{base_url}/get", params={"stock": 5})
        assert response.status_code == 200
        stock = int(response.json()["args"]["stock"])
        assert stock == 0, f"Product stock count mismatch: expected 0, got {stock}"

    @el.story("Product images")
    @el.severity("normal")
    def test_product_image_upload(self, http_session, base_url, tmp_path):
        """Upload product image via POST."""
        image_file = tmp_path / "product.txt"
        image_file.write_text("fake image content for upload test")

        with open(image_file, "rb") as f:
            response = http_session.post(
                f"{base_url}/post",
                files={"file": ("product.txt", f, "text/plain")},
                headers={},
            )

        assert response.status_code == 200
        el.attach("Uploaded file content", image_file.read_text())
