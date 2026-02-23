"""Tests for article folder service - tree structure, depth validation, drag&drop."""

import pytest
from unittest.mock import AsyncMock, MagicMock

from fastapi import HTTPException

from app.services.article_folder_service import ArticleFolderService, MAX_DEPTH


# ─── Fixtures ───────────────────────────────────────────────────────

@pytest.fixture
def mock_db():
    db = AsyncMock()
    db.commit = AsyncMock()
    db.flush = AsyncMock()
    db.refresh = AsyncMock()
    db.execute = AsyncMock()
    return db


def _make_folder(id="f1", name="Folder", parent_id=None, project_id="p1",
                 children=None, articles=None, sort_order=0):
    folder = MagicMock()
    folder.id = id
    folder.name = name
    folder.parent_id = parent_id
    folder.project_id = project_id
    folder.sort_order = sort_order
    folder.children = children or []
    folder.articles = articles or []
    return folder


def _make_article(id="a1", title="Article", slug="article", folder_id=None,
                  status="draft", created_at=None):
    article = MagicMock()
    article.id = id
    article.title = title
    article.slug = slug
    article.folder_id = folder_id
    article.status = status
    article.created_at = created_at
    article.project_id = "p1"
    return article


@pytest.fixture
def service(mock_db):
    svc = ArticleFolderService(mock_db)
    svc.repo = MagicMock()
    svc.article_repo = MagicMock()
    # Make all repo methods async
    svc.repo.get_by_id = AsyncMock()
    svc.repo.create = AsyncMock()
    svc.repo.delete = AsyncMock()
    svc.repo.get_tree = AsyncMock()
    svc.repo.get_depth = AsyncMock()
    svc.repo.get_by_name_and_parent = AsyncMock()
    svc.repo.get_children = AsyncMock()
    svc.repo.get_descendants = AsyncMock()
    svc.repo.get_max_subtree_depth = AsyncMock()
    svc.article_repo.get_by_id = AsyncMock()
    svc.article_repo.get_many_by_field = AsyncMock()
    return svc


# ─── Create Folder ──────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_create_root_folder(service):
    """Create root folder (no parent)."""
    new_folder = _make_folder()
    service.repo.get_by_name_and_parent.return_value = None
    service.repo.create.return_value = new_folder

    result = await service.create_folder("Folder", "p1")

    service.repo.create.assert_called_once()
    assert result.name == "Folder"


@pytest.mark.asyncio
async def test_create_child_folder(service):
    """Create child folder with valid parent."""
    parent = _make_folder(id="parent1")
    child = _make_folder(id="child1", parent_id="parent1")

    service.repo.get_by_id.return_value = parent
    service.repo.get_depth.return_value = 1  # parent at depth 1
    service.repo.get_by_name_and_parent.return_value = None
    service.repo.create.return_value = child

    result = await service.create_folder("Child", "p1", parent_id="parent1")

    assert result.parent_id == "parent1"


@pytest.mark.asyncio
async def test_create_folder_depth_exceeded(service):
    """Cannot create folder deeper than MAX_DEPTH."""
    parent = _make_folder(id="deep")
    service.repo.get_by_id.return_value = parent
    service.repo.get_depth.return_value = MAX_DEPTH  # already at max

    with pytest.raises(HTTPException) as exc:
        await service.create_folder("TooDeep", "p1", parent_id="deep")

    assert exc.value.status_code == 400
    assert "depth" in exc.value.detail.lower()


@pytest.mark.asyncio
async def test_create_folder_parent_not_found(service):
    """Cannot create folder with non-existent parent."""
    service.repo.get_by_id.return_value = None

    with pytest.raises(HTTPException) as exc:
        await service.create_folder("Orphan", "p1", parent_id="ghost")

    assert exc.value.status_code == 404


@pytest.mark.asyncio
async def test_create_folder_duplicate_name(service):
    """Cannot create folder with same name in same parent."""
    service.repo.get_by_name_and_parent.return_value = _make_folder()

    with pytest.raises(HTTPException) as exc:
        await service.create_folder("Duplicate", "p1")

    assert exc.value.status_code == 400
    assert "already exists" in exc.value.detail.lower()


@pytest.mark.asyncio
async def test_create_folder_empty_input(service):
    """Create folder with empty name still calls repo (validation is on router level)."""
    service.repo.get_by_name_and_parent.return_value = None
    service.repo.create.return_value = _make_folder(name="")

    result = await service.create_folder("", "p1")
    service.repo.create.assert_called_once()


# ─── Get Tree ────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_get_tree_empty(service):
    """Get tree returns empty list when no folders."""
    service.repo.get_tree.return_value = []

    result = await service.get_tree("p1")

    assert result == []


@pytest.mark.asyncio
async def test_get_tree_nested(service):
    """Get tree returns nested structure."""
    article = _make_article()
    child = _make_folder(id="c1", name="Child", parent_id="r1",
                         children=[], articles=[article])
    root = _make_folder(id="r1", name="Root", children=[child], articles=[])

    service.repo.get_tree.return_value = [root]

    result = await service.get_tree("p1")

    assert len(result) == 1
    assert result[0]["name"] == "Root"
    assert len(result[0]["children"]) == 1
    assert result[0]["children"][0]["name"] == "Child"
    assert result[0]["children"][0]["articles_count"] == 1


# ─── Update Folder ───────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_update_folder_success(service):
    """Update folder name."""
    folder = _make_folder(id="f1", name="Old")
    service.repo.get_by_id.return_value = folder
    service.repo.get_by_name_and_parent.return_value = None

    result = await service.update_folder("f1", "New", "p1")

    assert folder.name == "New"


@pytest.mark.asyncio
async def test_update_folder_not_found(service):
    """Update non-existent folder returns 404."""
    service.repo.get_by_id.return_value = None

    with pytest.raises(HTTPException) as exc:
        await service.update_folder("ghost", "New", "p1")

    assert exc.value.status_code == 404


@pytest.mark.asyncio
async def test_update_folder_duplicate_name(service):
    """Cannot rename to existing name in same parent."""
    folder = _make_folder(id="f1", name="Old")
    existing = _make_folder(id="f2", name="Taken")

    service.repo.get_by_id.return_value = folder
    service.repo.get_by_name_and_parent.return_value = existing

    with pytest.raises(HTTPException) as exc:
        await service.update_folder("f1", "Taken", "p1")

    assert exc.value.status_code == 400


@pytest.mark.asyncio
async def test_update_folder_same_name_same_id(service):
    """Renaming to same name (same folder ID) is OK."""
    folder = _make_folder(id="f1", name="Same")
    service.repo.get_by_id.return_value = folder
    service.repo.get_by_name_and_parent.return_value = folder  # same id

    result = await service.update_folder("f1", "Same", "p1")
    # Should not raise


# ─── Delete Folder ───────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_delete_folder_success(service):
    """Delete folder moves articles to parent."""
    folder = _make_folder(id="f1", parent_id="parent1")
    articles = [_make_article(id="a1", folder_id="f1")]

    service.repo.get_by_id.return_value = folder
    service.article_repo.get_many_by_field.return_value = articles
    service.repo.delete.return_value = True

    await service.delete_folder("f1")

    # Article moved to parent
    assert articles[0].folder_id == "parent1"
    service.repo.delete.assert_called_once_with("f1")


@pytest.mark.asyncio
async def test_delete_folder_not_found(service):
    """Delete non-existent folder returns 404."""
    service.repo.get_by_id.return_value = None

    with pytest.raises(HTTPException) as exc:
        await service.delete_folder("ghost")

    assert exc.value.status_code == 404


@pytest.mark.asyncio
async def test_delete_root_folder_articles_to_root(service):
    """Delete root folder moves articles to root (folder_id = None)."""
    folder = _make_folder(id="f1", parent_id=None)
    articles = [_make_article(id="a1", folder_id="f1")]

    service.repo.get_by_id.return_value = folder
    service.article_repo.get_many_by_field.return_value = articles
    service.repo.delete.return_value = True

    await service.delete_folder("f1")

    assert articles[0].folder_id is None


# ─── Move Folder ─────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_move_folder_success(service):
    """Move folder to new parent."""
    folder = _make_folder(id="f1", parent_id=None)

    service.repo.get_by_id.return_value = folder
    service.repo.get_descendants.return_value = []
    service.repo.get_depth.return_value = 1
    service.repo.get_max_subtree_depth.return_value = 0

    result = await service.move_folder("f1", "new_parent")

    assert folder.parent_id == "new_parent"


@pytest.mark.asyncio
async def test_move_folder_to_self(service):
    """Cannot move folder into itself."""
    folder = _make_folder(id="f1")
    service.repo.get_by_id.return_value = folder

    with pytest.raises(HTTPException) as exc:
        await service.move_folder("f1", "f1")

    assert exc.value.status_code == 400
    assert "itself" in exc.value.detail.lower()


@pytest.mark.asyncio
async def test_move_folder_to_descendant(service):
    """Cannot move folder into its own descendant."""
    folder = _make_folder(id="f1")
    service.repo.get_by_id.return_value = folder
    service.repo.get_descendants.return_value = ["c1", "c2"]

    with pytest.raises(HTTPException) as exc:
        await service.move_folder("f1", "c1")

    assert exc.value.status_code == 400
    assert "descendant" in exc.value.detail.lower()


@pytest.mark.asyncio
async def test_move_folder_depth_exceeded(service):
    """Cannot move if resulting depth exceeds MAX_DEPTH."""
    folder = _make_folder(id="f1")
    service.repo.get_by_id.return_value = folder
    service.repo.get_descendants.return_value = []
    service.repo.get_depth.return_value = 2  # parent at depth 2
    service.repo.get_max_subtree_depth.return_value = 1  # subtree depth 1
    # 2 + 1 + 1 = 4 > MAX_DEPTH(3)

    with pytest.raises(HTTPException) as exc:
        await service.move_folder("f1", "deep_parent")

    assert exc.value.status_code == 400
    assert "depth" in exc.value.detail.lower()


@pytest.mark.asyncio
async def test_move_folder_to_root(service):
    """Move folder to root (new_parent_id = None)."""
    folder = _make_folder(id="f1", parent_id="old_parent")
    service.repo.get_by_id.return_value = folder

    result = await service.move_folder("f1", None)

    assert folder.parent_id is None


@pytest.mark.asyncio
async def test_move_folder_not_found(service):
    """Move non-existent folder returns 404."""
    service.repo.get_by_id.return_value = None

    with pytest.raises(HTTPException) as exc:
        await service.move_folder("ghost", None)

    assert exc.value.status_code == 404


# ─── Move Article to Folder ─────────────────────────────────────────

@pytest.mark.asyncio
async def test_move_article_to_folder(service):
    """Move article to a folder."""
    article = _make_article(id="a1", folder_id=None)
    folder = _make_folder(id="f1")

    service.article_repo.get_by_id.return_value = article
    service.repo.get_by_id.return_value = folder

    await service.move_article_to_folder("a1", "f1")

    assert article.folder_id == "f1"


@pytest.mark.asyncio
async def test_move_article_to_root(service):
    """Move article to root (folder_id = None)."""
    article = _make_article(id="a1", folder_id="f1")
    service.article_repo.get_by_id.return_value = article

    await service.move_article_to_folder("a1", None)

    assert article.folder_id is None


@pytest.mark.asyncio
async def test_move_article_not_found(service):
    """Move non-existent article returns 404."""
    service.article_repo.get_by_id.return_value = None

    with pytest.raises(HTTPException) as exc:
        await service.move_article_to_folder("ghost", "f1")

    assert exc.value.status_code == 404


@pytest.mark.asyncio
async def test_move_article_to_nonexistent_folder(service):
    """Move article to non-existent folder returns 404."""
    article = _make_article(id="a1")
    service.article_repo.get_by_id.return_value = article
    service.repo.get_by_id.return_value = None

    with pytest.raises(HTTPException) as exc:
        await service.move_article_to_folder("a1", "ghost")

    assert exc.value.status_code == 404


# ─── None Handling ───────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_create_folder_none_parent(service):
    """Create folder with None parent_id creates root folder."""
    service.repo.get_by_name_and_parent.return_value = None
    service.repo.create.return_value = _make_folder()

    result = await service.create_folder("Root", "p1", parent_id=None)

    # get_by_id should NOT be called for None parent
    service.repo.get_by_id.assert_not_called()


@pytest.mark.asyncio
async def test_move_folder_none_handling(service):
    """Move to None parent should not check depth."""
    folder = _make_folder(id="f1", parent_id="old")
    service.repo.get_by_id.return_value = folder

    await service.move_folder("f1", None)

    service.repo.get_depth.assert_not_called()
    service.repo.get_descendants.assert_not_called()


# ─── MAX_DEPTH Constant ─────────────────────────────────────────────

def test_max_depth_is_3():
    """MAX_DEPTH should be 3."""
    assert MAX_DEPTH == 3
