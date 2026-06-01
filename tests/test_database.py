"""Tests for the comment lifecycle in database.py."""
from __future__ import annotations

import database


# ── Fixtures ──────────────────────────────────────────────────────────────────

def _setup(monkeypatch, tmp_path):
    db_path = tmp_path / "test.db"
    monkeypatch.setattr(database, "_DB_PATH", db_path)
    database.init_db()
    return db_path


# ── add_comment / get_comments ────────────────────────────────────────────────

def test_add_comment_returns_id(monkeypatch, tmp_path):
    _setup(monkeypatch, tmp_path)
    cid = database.add_comment("CH01_SC01", "alice", "Great scene", "viewer", paragraph_index=2)
    assert isinstance(cid, int)
    assert cid > 0


def test_get_comments_returns_added_entry(monkeypatch, tmp_path):
    _setup(monkeypatch, tmp_path)
    database.add_comment("CH01_SC01", "alice", "Great scene", "viewer", paragraph_index=2)
    comments = database.get_comments("CH01_SC01", paragraph_index=2)
    assert len(comments) == 1
    c = comments[0]
    assert c["content"] == "Great scene"
    assert c["username"] == "alice"
    assert c["comment_type"] == "viewer"
    assert c["resolved"] == 0


def test_get_comments_filters_by_paragraph(monkeypatch, tmp_path):
    _setup(monkeypatch, tmp_path)
    database.add_comment("CH01_SC01", "alice", "Para 1 note", "viewer", paragraph_index=1)
    database.add_comment("CH01_SC01", "alice", "Para 3 note", "viewer", paragraph_index=3)

    p1 = database.get_comments("CH01_SC01", paragraph_index=1)
    p3 = database.get_comments("CH01_SC01", paragraph_index=3)
    assert len(p1) == 1 and p1[0]["content"] == "Para 1 note"
    assert len(p3) == 1 and p3[0]["content"] == "Para 3 note"


def test_get_comments_filters_by_scene_key(monkeypatch, tmp_path):
    _setup(monkeypatch, tmp_path)
    database.add_comment("CH01_SC01", "alice", "Scene 1 note", "viewer")
    database.add_comment("CH01_SC02", "alice", "Scene 2 note", "viewer")

    assert len(database.get_comments("CH01_SC01")) == 1
    assert len(database.get_comments("CH01_SC02")) == 1
    assert len(database.get_comments("CH01_SC03")) == 0


# ── resolve_comment ───────────────────────────────────────────────────────────

def test_resolve_hides_comment_from_default_query(monkeypatch, tmp_path):
    _setup(monkeypatch, tmp_path)
    cid = database.add_comment("CH01_SC01", "alice", "To be removed", "viewer", paragraph_index=0)

    assert len(database.get_comments("CH01_SC01")) == 1
    database.resolve_comment(cid)
    assert len(database.get_comments("CH01_SC01")) == 0


def test_resolve_sets_resolved_flag(monkeypatch, tmp_path):
    _setup(monkeypatch, tmp_path)
    cid = database.add_comment("CH01_SC01", "alice", "Resolved note", "viewer")
    database.resolve_comment(cid)

    all_comments = database.get_comments("CH01_SC01", include_resolved=True)
    assert len(all_comments) == 1
    assert all_comments[0]["resolved"] == 1


def test_resolve_only_affects_target(monkeypatch, tmp_path):
    _setup(monkeypatch, tmp_path)
    cid_keep = database.add_comment("CH01_SC01", "alice", "Keep this", "viewer", paragraph_index=0)
    cid_remove = database.add_comment("CH01_SC01", "bob", "Remove this", "viewer", paragraph_index=0)

    database.resolve_comment(cid_remove)

    remaining = database.get_comments("CH01_SC01", paragraph_index=0)
    assert len(remaining) == 1
    assert remaining[0]["id"] == cid_keep


def test_resolve_nonexistent_is_noop(monkeypatch, tmp_path):
    _setup(monkeypatch, tmp_path)
    database.resolve_comment(99999)  # should not raise
    assert len(database.get_comments("CH01_SC01")) == 0


def test_multiple_comments_same_paragraph(monkeypatch, tmp_path):
    _setup(monkeypatch, tmp_path)
    database.add_comment("CH01_SC01", "alice", "Note A", "viewer", paragraph_index=5)
    database.add_comment("CH01_SC01", "bob", "Note B", "ai_prompt", paragraph_index=5)

    comments = database.get_comments("CH01_SC01", paragraph_index=5)
    assert len(comments) == 2
    types = {c["comment_type"] for c in comments}
    assert types == {"viewer", "ai_prompt"}
