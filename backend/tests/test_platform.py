"""Santé, CORS et stockage : les points touchés lors d'un déploiement."""

import pytest
from pydantic import SecretStr

from app.config import Settings
from app.main import make_storage
from app.storage import BlobStorage, LocalStorage


class FakeContainer:
    """Remplace un ContainerClient Azure : blobs gardés en mémoire, aucun appel réseau."""

    def __init__(self):
        self.blobs = {}

    def upload_blob(self, name, data, overwrite=False):
        self.blobs[name] = data

    def download_blob(self, name):
        content = self.blobs[name]
        return type("Downloader", (), {"readall": lambda self: content})()


def test_health_endpoints(client):
    assert client.get("/health/live").json() == {"status": "ok"}
    assert client.get("/health/ready").json() == {"status": "ok"}


@pytest.mark.parametrize("origin,allowed", [("http://localhost:5173", True), ("https://inconnu.test", False)])
def test_cors_allows_only_configured_origins(client, origin, allowed):
    response = client.options(
        "/api/documents", headers={"Origin": origin, "Access-Control-Request-Method": "GET"}
    )
    assert (response.headers.get("access-control-allow-origin") == origin) is allowed


def test_cors_origins_tolerate_spaces_and_trailing_slash():
    settings = Settings(_env_file=None, cors_origins=" https://front.test/ , http://localhost:5173")
    assert settings.cors_origin_list == ["https://front.test", "http://localhost:5173"]


def test_local_storage_round_trip(tmp_path):
    LocalStorage(tmp_path).put("doc.pdf", b"%PDF-test")
    assert LocalStorage(tmp_path).get("doc.pdf") == b"%PDF-test"  # nouvelle instance : fichier persistant


def test_local_storage_rejects_path_escape(tmp_path):
    with pytest.raises(ValueError):
        LocalStorage(tmp_path).get("../../secret.txt")


def test_blob_storage_round_trip():
    storage = BlobStorage(FakeContainer())
    storage.put("doc.pdf", b"%PDF-test")
    assert storage.get("doc.pdf") == b"%PDF-test"


def test_storage_is_local_without_connection_string(settings):
    assert isinstance(make_storage(settings), LocalStorage)


def test_storage_is_blob_with_connection_string(settings):
    settings.azure_storage_connection_string = SecretStr(
        "DefaultEndpointsProtocol=https;AccountName=test;AccountKey=dGVzdA==;EndpointSuffix=core.windows.net"
    )
    assert isinstance(make_storage(settings), BlobStorage)  # aucun appel réseau à la création
