"""Tests for message delete + edit-and-resend (rewind) history operations."""

from app.services import project_service as ps


def _fresh(monkeypatch, tmp_path):
    monkeypatch.setattr(ps, "_history_path", lambda pid: tmp_path / f"{pid}.json")


def test_history_remove_last_match(tmp_path, monkeypatch):
    _fresh(monkeypatch, tmp_path)
    ps.history_append("p", "user", "hello")
    ps.history_append("p", "assistant", "hi there")
    ps.history_append("p", "user", "hello")  # duplicate content — must remove LAST
    assert ps.history_remove("p", "user", "hello") is True
    left = ps.history_load("p")
    assert [m["content"] for m in left] == ["hello", "hi there"]
    assert ps.history_remove("p", "user", "nonexistent") is False


def test_history_rewind_drops_tail(tmp_path, monkeypatch):
    _fresh(monkeypatch, tmp_path)
    ps.history_append("p", "user", "first question")
    ps.history_append("p", "assistant", "first answer")
    ps.history_append("p", "user", "second question")
    ps.history_append("p", "assistant", "second answer")
    removed = ps.history_rewind("p", "second question")
    assert removed == 2
    left = ps.history_load("p")
    assert [m["content"] for m in left] == ["first question", "first answer"]
    assert ps.history_rewind("p", "never sent") == 0


def test_chat_service_sync(tmp_path, monkeypatch):
    _fresh(monkeypatch, tmp_path)
    from app.services.chat_service import ChatService
    from app.core import Message
    from app.utils import get_current_timestamp

    svc = ChatService()
    for role, content in [("user", "q1"), ("assistant", "a1"), ("user", "q2"), ("assistant", "a2")]:
        svc.append_message(Message(role=role, content=content,
                                   timestamp=get_current_timestamp()), "p")
    # rewind to q2: memory and disk both lose q2 + a2
    assert svc.rewind_to("q2", "p") == 2
    assert [m.content for m in svc._get_history("p")] == ["q1", "a1"]
    assert [m["content"] for m in ps.history_load("p")] == ["q1", "a1"]
    # delete a1 from both
    assert svc.remove_message("assistant", "a1", "p") is True
    assert [m.content for m in svc._get_history("p")] == ["q1"]


def test_routes_exist():
    from app.api.routes import chat, workspace
    chat_paths = {r.path for r in chat.router.routes}
    assert "/chat/message/delete" in chat_paths
    assert "/chat/message/rewind" in chat_paths
    ws_paths = {(r.path, tuple(sorted(r.methods))) for r in workspace.router.routes if hasattr(r, "methods")}
    assert ("/workspace/file", ("DELETE",)) in ws_paths
