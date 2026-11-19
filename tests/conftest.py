import os, sys, tempfile, pytest

# app.py creates and seeds its database at import time, so point it at a
# throwaway file before importing it.
os.environ["DB_PATH"] = os.path.join(tempfile.mkdtemp(), "test.db")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app as flask_app  # noqa: E402


@pytest.fixture
def client():
    flask_app.config["TESTING"] = True
    with flask_app.test_client() as c:
        yield c


def login(client, username="maya", password="password123"):
    return client.post("/login", data={"username": username, "password": password},
                       follow_redirects=True)
