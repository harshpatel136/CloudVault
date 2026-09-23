from app.models import File as FileModel
from app.models import DocumentChunk


def register_and_login(client, email, password="TestPassword123"):
    credentials = {
        "email": email,
        "password": password,
    }

    register_response = client.post(
        "/auth/register",
        json=credentials,
    )

    assert register_response.status_code == 200

    login_response = client.post(
        "/auth/login-json",
        json=credentials,
    )

    assert login_response.status_code == 200

    return login_response.json()["access_token"]


def create_file(db_session, user_id, filename="rag-test.pdf"):
    file_record = FileModel(
        original_filename=filename,
        object_key=f"uploads/{filename}",
        content_type="application/pdf",
        file_size=1024,
        user_id=user_id,
    )

    db_session.add(file_record)
    db_session.commit()
    db_session.refresh(file_record)

    return file_record


def create_chunk(
    db_session,
    file_id,
    chunk_index,
    text,
    page_number=1,
):
    chunk = DocumentChunk(
        file_id=file_id,
        chunk_index=chunk_index,
        text=text,
        page_number=page_number,
        embedding=[0.1] * 384,
    )

    db_session.add(chunk)
    db_session.commit()
    db_session.refresh(chunk)

    return chunk


def test_search_requires_authentication(client):
    response = client.get(
        "/files/1/search",
        params={"q": "test"},
    )

    assert response.status_code == 401


def test_chat_requires_authentication(client):
    response = client.get(
        "/files/1/chat",
        params={"q": "test"},
    )

    assert response.status_code == 401


def test_search_rejects_unknown_file(
    client,
):
    token = register_and_login(
        client,
        "unknown-search@example.com",
    )

    response = client.get(
        "/files/999/search",
        params={"q": "test"},
        headers={
            "Authorization": f"Bearer {token}",
        },
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "File not found"


def test_chat_rejects_unknown_file(
    client,
):
    token = register_and_login(
        client,
        "unknown-chat@example.com",
    )

    response = client.get(
        "/files/999/chat",
        params={"q": "test"},
        headers={
            "Authorization": f"Bearer {token}",
        },
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "File not found"


def test_search_rejects_empty_query(
    client,
    db_session,
):
    token = register_and_login(
        client,
        "empty-search@example.com",
    )

    user_response = client.get(
        "/users/me",
        headers={
            "Authorization": f"Bearer {token}",
        },
    )

    user_id = user_response.json()["id"]

    file_record = create_file(
        db_session,
        user_id,
    )

    response = client.get(
        f"/files/{file_record.id}/search",
        params={"q": "   "},
        headers={
            "Authorization": f"Bearer {token}",
        },
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Search query is required"


def test_chat_rejects_empty_question(
    client,
    db_session,
):
    token = register_and_login(
        client,
        "empty-chat@example.com",
    )

    user_response = client.get(
        "/users/me",
        headers={
            "Authorization": f"Bearer {token}",
        },
    )

    user_id = user_response.json()["id"]

    file_record = create_file(
        db_session,
        user_id,
    )

    response = client.get(
        f"/files/{file_record.id}/chat",
        params={"q": "   "},
        headers={
            "Authorization": f"Bearer {token}",
        },
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Question is required"


def test_search_returns_matching_chunks(
    client,
    db_session,
    monkeypatch,
):
    token = register_and_login(
        client,
        "search@example.com",
    )

    user_response = client.get(
        "/users/me",
        headers={
            "Authorization": f"Bearer {token}",
        },
    )

    user_id = user_response.json()["id"]

    file_record = create_file(
        db_session,
        user_id,
    )

    chunk = create_chunk(
        db_session,
        file_record.id,
        chunk_index=0,
        text="FastAPI provides a framework for building APIs.",
        page_number=2,
    )

    monkeypatch.setattr(
        "app.routes.files.semantic_search",
        lambda db, file_id, query, limit: [
            (chunk, 0.1234)
        ],
    )

    response = client.get(
        f"/files/{file_record.id}/search",
        params={"q": "FastAPI"},
        headers={
            "Authorization": f"Bearer {token}",
        },
    )

    assert response.status_code == 200

    data = response.json()

    assert data["file_id"] == file_record.id
    assert data["query"] == "FastAPI"

    assert len(data["results"]) == 1
    assert data["results"][0]["chunk_index"] == 0
    assert data["results"][0]["page_number"] == 2
    assert (
        data["results"][0]["text"]
        == "FastAPI provides a framework for building APIs."
    )
    assert data["results"][0]["distance"] == 0.1234


def test_chat_returns_answer_and_sources(
    client,
    db_session,
    monkeypatch,
):
    token = register_and_login(
        client,
        "rag-chat@example.com",
    )

    user_response = client.get(
        "/users/me",
        headers={
            "Authorization": f"Bearer {token}",
        },
    )

    user_id = user_response.json()["id"]

    file_record = create_file(
        db_session,
        user_id,
    )

    monkeypatch.setattr(
        "app.routes.files.answer_question",
        lambda db, file_id, question: {
            "answer": "FastAPI is a Python web framework.",
            "sources": [
                {
                    "chunk_index": 0,
                    "page_number": 1,
                    "distance": 0.1234,
                }
            ],
        },
    )

    response = client.get(
        f"/files/{file_record.id}/chat",
        params={"q": "What is FastAPI?"},
        headers={
            "Authorization": f"Bearer {token}",
        },
    )

    assert response.status_code == 200

    data = response.json()

    assert data["file_id"] == file_record.id
    assert data["question"] == "What is FastAPI?"
    assert data["answer"] == "FastAPI is a Python web framework."

    assert len(data["sources"]) == 1
    assert data["sources"][0]["chunk_index"] == 0
    assert data["sources"][0]["page_number"] == 1
    assert data["sources"][0]["distance"] == 0.1234


def test_user_cannot_search_another_users_document(
    client,
    db_session,
    monkeypatch,
):
    owner_token = register_and_login(
        client,
        "rag-owner@example.com",
    )

    owner_response = client.get(
        "/users/me",
        headers={
            "Authorization": f"Bearer {owner_token}",
        },
    )

    owner_id = owner_response.json()["id"]

    file_record = create_file(
        db_session,
        owner_id,
    )

    search_called = []

    monkeypatch.setattr(
        "app.routes.files.semantic_search",
        lambda *args, **kwargs: search_called.append(True),
    )

    other_token = register_and_login(
        client,
        "rag-other@example.com",
    )

    response = client.get(
        f"/files/{file_record.id}/search",
        params={"q": "test"},
        headers={
            "Authorization": f"Bearer {other_token}",
        },
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "File not found"
    assert search_called == []


def test_user_cannot_chat_with_another_users_document(
    client,
    db_session,
    monkeypatch,
):
    owner_token = register_and_login(
        client,
        "rag-chat-owner@example.com",
    )

    owner_response = client.get(
        "/users/me",
        headers={
            "Authorization": f"Bearer {owner_token}",
        },
    )

    owner_id = owner_response.json()["id"]

    file_record = create_file(
        db_session,
        owner_id,
    )

    chat_called = []

    monkeypatch.setattr(
        "app.routes.files.answer_question",
        lambda *args, **kwargs: chat_called.append(True),
    )

    other_token = register_and_login(
        client,
        "rag-chat-other@example.com",
    )

    response = client.get(
        f"/files/{file_record.id}/chat",
        params={"q": "test"},
        headers={
            "Authorization": f"Bearer {other_token}",
        },
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "File not found"
    assert chat_called == []