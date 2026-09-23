from app.models import File as FileModel


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


def create_file(db_session, user_id, filename="test.pdf"):
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


def test_list_files_requires_authentication(client):
    response = client.get("/files/")

    assert response.status_code == 401


def test_list_files_rejects_invalid_token(client):
    response = client.get(
        "/files/",
        headers={"Authorization": "Bearer invalid-token"},
    )

    assert response.status_code == 401


def test_authenticated_user_can_list_files(client, db_session):
    token = register_and_login(
        client,
        "files@example.com",
    )

    user_response = client.get(
        "/users/me",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert user_response.status_code == 200

    user_id = user_response.json()["id"]

    create_file(
        db_session,
        user_id,
        "my-file.pdf",
    )

    response = client.get(
        "/files/",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200

    files = response.json()

    assert len(files) == 1
    assert files[0]["filename"] == "my-file.pdf"
    assert files[0]["content_type"] == "application/pdf"
    assert files[0]["user_id"] == user_id


def test_user_cannot_download_another_users_file(
    client,
    db_session,
):
    owner_token = register_and_login(
        client,
        "owner@example.com",
    )

    owner_response = client.get(
        "/users/me",
        headers={"Authorization": f"Bearer {owner_token}"},
    )

    owner_id = owner_response.json()["id"]

    file_record = create_file(
        db_session,
        owner_id,
        "private.pdf",
    )

    other_token = register_and_login(
        client,
        "other@example.com",
    )

    response = client.get(
        f"/files/{file_record.id}/download",
        headers={"Authorization": f"Bearer {other_token}"},
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "File not found"


def test_user_cannot_search_another_users_file(
    client,
    db_session,
):
    owner_token = register_and_login(
        client,
        "search-owner@example.com",
    )

    owner_response = client.get(
        "/users/me",
        headers={"Authorization": f"Bearer {owner_token}"},
    )

    owner_id = owner_response.json()["id"]

    file_record = create_file(
        db_session,
        owner_id,
        "search.pdf",
    )

    other_token = register_and_login(
        client,
        "search-other@example.com",
    )

    response = client.get(
        f"/files/{file_record.id}/search",
        params={"q": "test"},
        headers={"Authorization": f"Bearer {other_token}"},
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "File not found"


def test_user_cannot_chat_with_another_users_file(
    client,
    db_session,
):
    owner_token = register_and_login(
        client,
        "chat-owner@example.com",
    )

    owner_response = client.get(
        "/users/me",
        headers={"Authorization": f"Bearer {owner_token}"},
    )

    owner_id = owner_response.json()["id"]

    file_record = create_file(
        db_session,
        owner_id,
        "chat.pdf",
    )

    other_token = register_and_login(
        client,
        "chat-other@example.com",
    )

    response = client.get(
        f"/files/{file_record.id}/chat",
        params={"q": "What is this?"},
        headers={"Authorization": f"Bearer {other_token}"},
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "File not found"


def test_download_generates_presigned_url(
    client,
    db_session,
    monkeypatch,
):
    token = register_and_login(
        client,
        "download@example.com",
    )

    user_response = client.get(
        "/users/me",
        headers={"Authorization": f"Bearer {token}"},
    )

    user_id = user_response.json()["id"]

    file_record = create_file(
        db_session,
        user_id,
        "download.pdf",
    )

    monkeypatch.setattr(
        "app.routes.files.generate_download_url",
        lambda object_key: "https://example.com/presigned-url",
    )

    response = client.get(
        f"/files/{file_record.id}/download",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200

    data = response.json()

    assert data["id"] == file_record.id
    assert data["filename"] == "download.pdf"
    assert data["download_url"] == "https://example.com/presigned-url"
    assert data["expires_in"] == 300


def test_delete_file(
    client,
    db_session,
    monkeypatch,
):
    token = register_and_login(
        client,
        "delete@example.com",
    )

    user_response = client.get(
        "/users/me",
        headers={"Authorization": f"Bearer {token}"},
    )

    user_id = user_response.json()["id"]

    file_record = create_file(
        db_session,
        user_id,
        "delete.pdf",
    )

    deleted_keys = []

    monkeypatch.setattr(
        "app.routes.files.delete_file",
        lambda object_key: deleted_keys.append(object_key),
    )

    response = client.delete(
        f"/files/{file_record.id}",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200

    data = response.json()

    assert data["message"] == "File deleted successfully"
    assert data["id"] == file_record.id
    assert deleted_keys == ["uploads/delete.pdf"]

    deleted_file = (
        db_session.query(FileModel)
        .filter(FileModel.id == file_record.id)
        .first()
    )

    assert deleted_file is None


def test_user_cannot_delete_another_users_file(
    client,
    db_session,
    monkeypatch,
):
    owner_token = register_and_login(
        client,
        "delete-owner@example.com",
    )

    owner_response = client.get(
        "/users/me",
        headers={"Authorization": f"Bearer {owner_token}"},
    )

    owner_id = owner_response.json()["id"]

    file_record = create_file(
        db_session,
        owner_id,
        "protected-delete.pdf",
    )

    other_token = register_and_login(
        client,
        "delete-other@example.com",
    )

    delete_called = []

    monkeypatch.setattr(
        "app.routes.files.delete_file",
        lambda object_key: delete_called.append(object_key),
    )

    response = client.delete(
        f"/files/{file_record.id}",
        headers={"Authorization": f"Bearer {other_token}"},
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "File not found"
    assert delete_called == []


def test_upload_rejects_non_pdf(
    client,
    monkeypatch,
):
    token = register_and_login(
        client,
        "upload-validation@example.com",
    )

    upload_called = []

    monkeypatch.setattr(
        "app.routes.files.upload_file",
        lambda *args, **kwargs: upload_called.append(True),
    )

    response = client.post(
        "/files/upload",
        headers={"Authorization": f"Bearer {token}"},
        files={
            "file": (
                "test.txt",
                b"not a pdf",
                "text/plain",
            )
        },
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Only PDF files are allowed"
    assert upload_called == []


def test_upload_rejects_invalid_pdf_signature(
    client,
    monkeypatch,
):
    token = register_and_login(
        client,
        "invalid-pdf@example.com",
    )

    upload_called = []

    monkeypatch.setattr(
        "app.routes.files.upload_file",
        lambda *args, **kwargs: upload_called.append(True),
    )

    response = client.post(
        "/files/upload",
        headers={"Authorization": f"Bearer {token}"},
        files={
            "file": (
                "fake.pdf",
                b"this is not a real pdf",
                "application/pdf",
            )
        },
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Invalid PDF file"
    assert upload_called == []


def test_upload_pdf_with_mocked_s3_and_processing(
    client,
    monkeypatch,
):
    token = register_and_login(
        client,
        "upload@example.com",
    )

    uploaded = []
    processed = []

    monkeypatch.setattr(
        "app.routes.files.upload_file",
        lambda temp_path, object_key, content_type: uploaded.append(
            {
                "object_key": object_key,
                "content_type": content_type,
            }
        ),
    )

    monkeypatch.setattr(
        "app.routes.files.process_file",
        lambda db, file: processed.append(file.id)
        or {
            "pages": 1,
            "chunks": 1,
            "embeddings": 1,
        },
    )

    response = client.post(
        "/files/upload",
        headers={"Authorization": f"Bearer {token}"},
        files={
            "file": (
                "document.pdf",
                b"%PDF-test-content",
                "application/pdf",
            )
        },
    )

    assert response.status_code == 200

    data = response.json()

    assert data["filename"] == "document.pdf"
    assert data["content_type"] == "application/pdf"
    assert data["file_size"] == len(b"%PDF-test-content")
    assert data["processing"] == {
        "pages": 1,
        "chunks": 1,
        "embeddings": 1,
    }

    assert len(uploaded) == 1
    assert uploaded[0]["object_key"].startswith("uploads/")
    assert uploaded[0]["object_key"].endswith(".pdf")
    assert uploaded[0]["content_type"] == "application/pdf"

    assert len(processed) == 1