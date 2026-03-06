from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient

from backend.error_handlers import install_error_handlers


def test_generic_exception_wrapped_to_500():
    app = FastAPI()
    install_error_handlers(app)

    @app.get("/boom")
    def boom():  # type: ignore[return-type]
        raise RuntimeError("kaboom")

    client = TestClient(app, raise_server_exceptions=False)
    r = client.get("/boom")
    assert r.status_code == 500
    body = r.json()
    assert body["code"] == "INTERNAL_ERROR"
    assert "RuntimeError" in body["message"]


def test_http_exception_passes_through():
    app = FastAPI()
    install_error_handlers(app)

    @app.get("/http")
    def raise_http():  # type: ignore[return-type]
        raise HTTPException(status_code=418, detail="teapot")

    client = TestClient(app, raise_server_exceptions=False)
    r = client.get("/http")
    assert r.status_code == 418
    assert r.json()["detail"] == "teapot"
