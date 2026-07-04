import pytest
pytest.importorskip("fastapi")

from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.routes.health import router


def _client(ready_ok=True):
    app = FastAPI()

    class FakeEngine:
        def connect(self):
            if not ready_ok:
                raise RuntimeError("db down")

            class C:
                def __enter__(self): return self
                def __exit__(self, *a): return False
                def exec_driver_sql(self, q): return None
            return C()

    class Nova:
        engine = FakeEngine()
    app.state.nova = Nova()
    app.include_router(router)
    return TestClient(app)


def test_health_liveness_ok():
    assert _client().get("/health").json() == {"status": "ok"}


def test_health_ready_ok():
    assert _client(ready_ok=True).get("/health/ready").status_code == 200


def test_health_ready_503_when_db_down():
    assert _client(ready_ok=False).get("/health/ready").status_code == 503
