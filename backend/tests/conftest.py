import os

from cryptography.fernet import Fernet

# Configure before any app module reads settings. Tests always use a dedicated *_test database
# (its schema is dropped on every run), never the URL from backend/.env.
os.environ["IPP_ENVIRONMENT"] = "test"
os.environ["IPP_COOKIE_SECURE"] = "false"
os.environ["IPP_OPENROUTER_API_KEY"] = ""  # tests never reach the real provider
os.environ["IPP_EMBEDDED_WORKER"] = "false"  # tests run queued jobs explicitly
os.environ["IPP_SOURCES_ALLOW_PRIVATE_NETWORKS"] = "false"
# A throwaway credential key, generated per test run.
os.environ["IPP_CREDENTIALS_KEYS"] = Fernet.generate_key().decode()
os.environ["IPP_DATABASE_URL"] = os.environ.get(
    "IPP_TEST_DATABASE_URL", "postgresql+psycopg://ipp:ipp@localhost:55432/ipp_test"
)

from collections.abc import Callable, Iterator  # noqa: E402
from pathlib import Path  # noqa: E402

import pytest  # noqa: E402
from alembic import command  # noqa: E402
from alembic.config import Config  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import text  # noqa: E402
from sqlalchemy.orm import Session  # noqa: E402

from app.auth.rbac import sync_rbac  # noqa: E402
from app.core.db import SessionLocal, engine  # noqa: E402
from app.core.email import EmailMessage, get_email_sender  # noqa: E402
from app.core.rate_limit import reset_all_rate_limits  # noqa: E402
from app.main import app  # noqa: E402
from app.models import Base  # noqa: E402

BACKEND_DIR = Path(__file__).resolve().parents[1]


def alembic_config() -> Config:
    cfg = Config(str(BACKEND_DIR / "alembic.ini"))
    cfg.attributes["configure_logger"] = False
    return cfg


@pytest.fixture(scope="session", autouse=True)
def _database() -> Iterator[None]:
    if not (engine.url.database or "").endswith("_test"):
        pytest.exit("Refusing to run tests against a non-test database.", returncode=1)
    with engine.begin() as conn:
        conn.execute(text("DROP SCHEMA public CASCADE"))
        conn.execute(text("CREATE SCHEMA public"))
    command.upgrade(alembic_config(), "head")
    yield


@pytest.fixture(autouse=True)
def _clean_state(_database: None) -> Iterator[None]:
    with SessionLocal() as db:
        sync_rbac(db)
    reset_all_rate_limits()
    yield
    app.dependency_overrides.clear()
    tables = ", ".join(t.name for t in Base.metadata.sorted_tables)
    with engine.begin() as conn:
        conn.execute(text(f"TRUNCATE {tables} RESTART IDENTITY CASCADE"))


@pytest.fixture
def db() -> Iterator[Session]:
    with SessionLocal() as session:
        yield session


@pytest.fixture
def make_client() -> Iterator[Callable[..., TestClient]]:
    """Each client has its own cookie jar, i.e. behaves like a separate browser/device."""
    clients: list[TestClient] = []

    def factory(*, csrf_header: bool = True) -> TestClient:
        headers = {"X-Requested-With": "ipp-web"} if csrf_header else {}
        client = TestClient(app, headers=headers)
        clients.append(client)
        return client

    yield factory
    for client in clients:
        client.close()


@pytest.fixture
def client(make_client: Callable[..., TestClient]) -> TestClient:
    return make_client()


class Outbox:
    def __init__(self) -> None:
        self.messages: list[EmailMessage] = []

    def send(self, message: EmailMessage) -> None:
        self.messages.append(message)


@pytest.fixture
def outbox() -> Outbox:
    box = Outbox()
    app.dependency_overrides[get_email_sender] = lambda: box
    return box
