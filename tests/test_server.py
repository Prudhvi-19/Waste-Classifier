from io import BytesIO

import pytest
from PIL import Image
from starlette.testclient import TestClient

from app import server


@pytest.fixture
def png():
    buffer = BytesIO()
    Image.new("RGB", (32, 32), "green").save(buffer, format="PNG")
    return buffer.getvalue()


@pytest.fixture
def client():
    with TestClient(server.create_app(predictor=lambda data: "R")) as client:
        yield client


def test_home_static_and_health(client, monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    assert client.get("/").status_code == 200
    assert client.get("/static/client.js").status_code == 200
    assert client.get("/health").json() == {"status": "ok"}
    assert client.get("/static/../server.py").status_code == 404


def test_prediction_response_contract(client, png):
    response = client.post("/analyze", files={"file": ("sample.png", png, "image/png")})
    assert response.status_code == 200
    assert response.json() == {"result": "R"}


def test_missing_model_is_explicit_and_home_still_loads(tmp_path):
    with TestClient(server.create_app(model_path=tmp_path / "missing.pkl")) as client:
        assert client.get("/").status_code == 200
        assert client.get("/health").status_code == 503
        assert client.post("/analyze").status_code == 503


def test_corrupt_model_is_unavailable(tmp_path):
    model = tmp_path / "export.pkl"
    model.write_bytes(b"not a pickle")
    with TestClient(server.create_app(model_path=model)) as client:
        assert client.get("/health").json() == {"status": "model_unavailable"}


def test_missing_file(client):
    assert client.post("/analyze").status_code == 400


def test_invalid_image(client):
    response = client.post("/analyze", files={"file": ("fake.png", b"not an image", "image/png")})
    assert response.status_code == 400


def test_multiple_files_rejected(client, png):
    response = client.post("/analyze", files=[("file", ("a.png", png)), ("file", ("b.png", png))])
    assert response.status_code == 400


def test_extra_fields_rejected(client, png):
    assert client.post("/analyze", data={"extra": "value"}, files={"file": ("a.png", png)}).status_code == 400


def test_file_limit(client, monkeypatch):
    monkeypatch.setattr(server, "MAX_IMAGE_BYTES", 10)
    response = client.post("/analyze", files={"file": ("a.png", b"x" * 11)})
    assert response.status_code == 413


def test_streaming_body_limit_without_content_length(client, monkeypatch):
    monkeypatch.setattr(server, "MAX_REQUEST_BYTES", 10)
    response = client.post("/analyze", content=iter([b"a" * 6, b"b" * 6]))
    assert response.status_code == 413


def test_pixel_limit(client, png, monkeypatch):
    monkeypatch.setattr(server, "MAX_IMAGE_PIXELS", 100)
    assert client.post("/analyze", files={"file": ("a.png", png)}).status_code == 400


def test_malformed_multipart(client):
    assert client.post("/analyze", content=b"bad", headers={"Content-Type": "multipart/form-data"}).status_code == 400


def test_method_and_cors(client):
    assert client.get("/analyze").status_code == 405
    response = client.options("/analyze", headers={"Origin": "https://example.com", "Access-Control-Request-Method": "POST"})
    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "*"
