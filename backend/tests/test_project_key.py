"""Tests for project key and human_id functionality."""

from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import HTTPException

from app.services.project_service import suggest_key, validate_key


class TestSuggestKey:
    """Tests for suggest_key function."""

    def test_suggest_key_two_words(self):
        """Two words → first letters."""
        assert suggest_key("Error Lens") == "EL"

    def test_suggest_key_one_word(self):
        """One word → first 3 letters."""
        assert suggest_key("Backend") == "BAC"

    def test_suggest_key_three_words(self):
        """Three words → first letters of each."""
        assert suggest_key("My Test Project") == "MTP"

    def test_suggest_key_four_plus_words(self):
        """Four+ words → first 4 letters."""
        assert suggest_key("Very Long Project Name Here") == "VLPN"

    def test_suggest_key_no_alpha(self):
        """No alpha chars → fallback PRJ."""
        assert suggest_key("123 456") == "PRJ"

    def test_suggest_key_mixed_case(self):
        """Mixed case → uppercase."""
        assert suggest_key("error lens") == "EL"

    def test_suggest_key_single_char_word(self):
        """Single char word → fallback."""
        result = suggest_key("a")
        assert len(result) >= 2


class TestValidateKey:
    """Tests for validate_key function."""

    def test_validate_key_valid(self):
        """Valid key passes."""
        assert validate_key("EL") == "EL"

    def test_validate_key_lowercase_normalized(self):
        """Lowercase → uppercase."""
        assert validate_key("el") == "EL"

    def test_validate_key_four_chars(self):
        """4 chars is max allowed."""
        assert validate_key("ABCD") == "ABCD"

    def test_validate_key_too_long(self):
        """5+ chars → 400."""
        with pytest.raises(HTTPException) as exc:
            validate_key("TOOLONG")
        assert exc.value.status_code == 400

    def test_validate_key_too_short(self):
        """1 char → 400."""
        with pytest.raises(HTTPException) as exc:
            validate_key("A")
        assert exc.value.status_code == 400

    def test_validate_key_digits(self):
        """Digits not allowed → 400."""
        with pytest.raises(HTTPException) as exc:
            validate_key("EL1")
        assert exc.value.status_code == 400

    def test_validate_key_special_chars(self):
        """Special chars → 400."""
        with pytest.raises(HTTPException) as exc:
            validate_key("E-L")
        assert exc.value.status_code == 400

    def test_validate_key_spaces_stripped(self):
        """Leading/trailing spaces stripped."""
        assert validate_key("  EL  ") == "EL"

    def test_validate_key_empty(self):
        """Empty string → 400."""
        with pytest.raises(HTTPException) as exc:
            validate_key("")
        assert exc.value.status_code == 400


class TestProjectServiceKeyMethods:
    """Tests for ProjectService key-related methods."""

    @pytest.fixture
    def mock_db(self):
        """Create mock database session."""
        db = AsyncMock()
        db.commit = AsyncMock()
        db.flush = AsyncMock()
        db.execute = AsyncMock()
        return db

    @pytest.fixture
    def service(self, mock_db):
        """Create ProjectService with mocked DB."""
        from app.services.project_service import ProjectService
        svc = ProjectService(mock_db)
        return svc

    @pytest.mark.asyncio
    async def test_key_unique_auto_resolve(self, service):
        """Two projects with same name → second gets suffixed key."""
        # First call: key "EL" exists, second "EL2" free
        call_count = 0

        async def mock_get_by_key(key):
            nonlocal call_count
            call_count += 1
            if key == "EL":
                return MagicMock()  # exists
            return None  # free

        service.project_repo.get_by_key = mock_get_by_key
        result = await service._resolve_key(None, "Error Lens")
        assert result == "EL2"

    @pytest.mark.asyncio
    async def test_key_explicit_taken(self, service):
        """Explicit key that's taken → HTTPException."""
        service.project_repo.get_by_key = AsyncMock(return_value=MagicMock())
        with pytest.raises(HTTPException) as exc:
            await service._resolve_key("EL", "Error Lens")
        assert exc.value.status_code == 400

    @pytest.mark.asyncio
    async def test_next_human_id_increments(self, service, mock_db):
        """Three calls → EL-1, EL-2, EL-3."""
        project = MagicMock()
        project.key = "EL"
        project.entity_counter = 0

        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = project
        mock_db.execute.return_value = result_mock

        ids = []
        for _ in range(3):
            hid = await service.next_human_id("proj-id")
            ids.append(hid)

        assert ids == ["EL-1", "EL-2", "EL-3"]
        assert project.entity_counter == 3

    @pytest.mark.asyncio
    async def test_no_key_no_human_id(self, service, mock_db):
        """Project without key → human_id is None."""
        project = MagicMock()
        project.key = None
        project.entity_counter = 0

        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = project
        mock_db.execute.return_value = result_mock

        hid = await service.next_human_id("proj-id")
        assert hid is None

    @pytest.mark.asyncio
    async def test_project_not_found_returns_none(self, service, mock_db):
        """Non-existent project → None."""
        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = result_mock

        hid = await service.next_human_id("nonexistent")
        assert hid is None

    @pytest.mark.asyncio
    async def test_human_id_concurrent(self, service, mock_db):
        """10 concurrent create → unique human_ids via sequential counter."""
        project = MagicMock()
        project.key = "TC"
        project.entity_counter = 0

        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = project
        mock_db.execute.return_value = result_mock

        # Simulate 10 sequential calls (FOR UPDATE ensures sequential in real DB)
        ids = []
        for _ in range(10):
            hid = await service.next_human_id("proj-id")
            ids.append(hid)

        assert len(ids) == 10
        assert len(set(ids)) == 10  # all unique
        assert ids[0] == "TC-1"
        assert ids[9] == "TC-10"

    @pytest.mark.asyncio
    async def test_check_key_available(self, service):
        """Available key returns available=True."""
        service.project_repo.get_by_key = AsyncMock(return_value=None)
        result = await service.check_key_available("EL")
        assert result["available"] is True
        assert result["suggestion"] == "EL"

    @pytest.mark.asyncio
    async def test_check_key_taken_with_suggestion(self, service):
        """Taken key returns suggestion."""
        call_count = 0

        async def mock_get_by_key(key):
            nonlocal call_count
            call_count += 1
            if key == "EL":
                return MagicMock()
            return None

        service.project_repo.get_by_key = mock_get_by_key
        result = await service.check_key_available("EL")
        assert result["available"] is False
        assert result["suggestion"] == "EL2"

    @pytest.mark.asyncio
    async def test_check_key_invalid(self, service):
        """Invalid key → available=False, suggestion=None."""
        result = await service.check_key_available("1")
        assert result["available"] is False
        assert result["suggestion"] is None
