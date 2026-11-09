from pathlib import Path


class LocalStorage:
    """Stockage des PDF dans un dossier local.

    Pour utiliser un autre stockage, écrire une classe avec les mêmes méthodes `put` et `get`,
    puis l'instancier dans `create_app` (app/main.py). Le reste de l'application ne change pas.
    """

    def __init__(self, root: Path):
        self.root = root.resolve()

    def put(self, key: str, content: bytes) -> None:
        path = self._path(key)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)

    def get(self, key: str) -> bytes:
        return self._path(key).read_bytes()

    def _path(self, key: str) -> Path:
        path = (self.root / key).resolve()
        if not path.is_relative_to(self.root):  # refuse « ../../fichier »
            raise ValueError(f"Clé de stockage invalide : {key}")
        return path


class BlobStorage:
    """Stockage des PDF dans un conteneur Azure Blob Storage (un blob par PDF, nommé par sa clé)."""

    def __init__(self, container):
        self.container = container  # azure.storage.blob.ContainerClient

    @classmethod
    def from_connection_string(cls, connection_string: str, container_name: str) -> "BlobStorage":
        from azure.storage.blob import ContainerClient

        return cls(ContainerClient.from_connection_string(connection_string, container_name))

    def put(self, key: str, content: bytes) -> None:
        self.container.upload_blob(key, content, overwrite=True)

    def get(self, key: str) -> bytes:
        return self.container.download_blob(key).readall()
