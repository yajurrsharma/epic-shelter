import os
import ctypes
import platform
import sqlite3
import zstandard as zstd
from typing import List, Optional, Tuple
from concurrent.futures import ThreadPoolExecutor
from models import Chunk, Manifest



"""

FOLLOWED GUIDE FROM https://joshleeb.com/posts/gearhash.html
FOR GEAR HASHING AND FASTCDC

"""


def get_user_config_dir() -> str:

    """Returns the platform-specific user configuration directory for DB replication."""

    if platform.system() == "Windows":
        base_dir = os.environ.get("APPDATA", os.path.expanduser("~"))
    else:
        base_dir = os.path.expanduser("~/.config")
    
    config_dir = os.path.join(base_dir, "shelter", "backups")
    os.makedirs(config_dir, exist_ok=True)
    return config_dir


def hide_directory(path: str) -> None:

    """
    Ensures a directory is hidden across Linux, macOS, and Windows.
    """
    
    if platform.system() == "Windows":
        FILE_ATTRIBUTE_HIDDEN = 0x02
        try:
            success = ctypes.windll.kernel32.SetFileAttributesW(str(path), FILE_ATTRIBUTE_HIDDEN)
            if not success:
                os.system(f'attrib +h "{path}"')
        except Exception:
            pass


class Vault:
    """
    Manages ACID transactions with SQLite and stores physical chunk files 
    inside the content-addressed storage repository with smart zstd compression.
    Automatically replicates metadata to the user configuration directory.
    """

    def __init__(self, vault_path: str = ".shelter"):
        self.vault_path = os.path.abspath(vault_path)
        self.db_path = os.path.join(self.vault_path, "shelter.db")
        self.chunks_dir = os.path.join(self.vault_path, "chunks")
        self.backup_dir = get_user_config_dir()

        self.compressor = zstd.ZstdCompressor(level=1)
        self.decompressor = zstd.ZstdDecompressor()

        self._initialize_vault()

    def _initialize_vault(self) -> None:
        """
        Creates the vault folder structure and SQLite metadata tables if they don't exist.
        Hides the vault folder on Windows.
        """
        os.makedirs(self.chunks_dir, exist_ok=True)
        hide_directory(self.vault_path)

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("PRAGMA journal_mode=WAL;")

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS chunks (
                    hash TEXT PRIMARY KEY,
                    size INTEGER NOT NULL,
                    ref_count INTEGER NOT NULL
                );
            """)

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS manifests (
                    snapshot_id TEXT PRIMARY KEY,
                    original_path TEXT NOT NULL,
                    data JSON NOT NULL,
                    created_at REAL NOT NULL
                );
            """)

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS config (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                );
            """)
            conn.commit()

        self._auto_backup_db()

    def _auto_backup_db(self) -> None:
        """
        Uses SQLite's Online Backup API to safely replicate the database 
        to ~/.config/shelter/backups/ without blocking active operations.
        """
        try:
            backup_db_path = os.path.join(self.backup_dir, "shelter_backup.db")
            
            with sqlite3.connect(self.db_path) as source_conn:
                with sqlite3.connect(backup_db_path) as dest_conn:
                    source_conn.backup(dest_conn)
        except Exception:
            pass

    def get_config(self, key: str) -> Optional[str]:
        """Fetches a configuration setting value by key."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT value FROM config WHERE key = ?", (key,))
            row = cursor.fetchone()
            return row[0] if row else None

    def set_config(self, key: str, value: str) -> None:
        """Sets or updates a configuration setting value by key."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO config (key, value) VALUES (?, ?) ON CONFLICT(key) DO UPDATE SET value = excluded.value",
                (key, value)
            )
            conn.commit()
        self._auto_backup_db()

    def _process_and_write_chunk(self, chunk: Chunk) -> Tuple[Chunk, bool]:
        """Worker method to compress and write a single chunk file in parallel."""
        subdir = os.path.join(self.chunks_dir, chunk.hash[:2], chunk.hash[2:4])
        os.makedirs(subdir, exist_ok=True)
        chunk_file_path = os.path.join(subdir, chunk.hash)

        if os.path.exists(chunk_file_path):
            return chunk, False

        if chunk.data is not None:
            compressed_bytes = self.compressor.compress(chunk.data)
            data_to_write = compressed_bytes if len(compressed_bytes) < len(chunk.data) else chunk.data

            with open(chunk_file_path, "wb") as f:
                f.write(data_to_write)

        return chunk, True

    def store_chunk(self, chunk: Chunk) -> bool:
        """
        Stores a single chunk into the vault if it doesn't exist.
        """
        chunk, is_new = self._process_and_write_chunk(chunk)

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT ref_count FROM chunks WHERE hash = ?", (chunk.hash,))
            row = cursor.fetchone()

            if row is None:
                cursor.execute(
                    "INSERT INTO chunks (hash, size, ref_count) VALUES (?, ?, ?)",
                    (chunk.hash, chunk.size, 1)
                )
            else:
                cursor.execute(
                    "UPDATE chunks SET ref_count = ref_count + 1 WHERE hash = ?",
                    (chunk.hash,)
                )

            conn.commit()

        self._auto_backup_db()
        return is_new

    def store_chunks_batch(self, chunks: List[Chunk]) -> int:
        """
        Stores multiple chunks in parallel across available CPU threads, 
        then updates SQLite metadata in a single WAL transaction.
        """
        if not chunks:
            return 0

        with ThreadPoolExecutor() as executor:
            results = list(executor.map(self._process_and_write_chunk, chunks))

        new_chunk_count = 0

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            for chunk, is_new in results:
                cursor.execute("SELECT ref_count FROM chunks WHERE hash = ?", (chunk.hash,))
                row = cursor.fetchone()

                if row is None:
                    cursor.execute(
                        "INSERT INTO chunks (hash, size, ref_count) VALUES (?, ?, ?)",
                        (chunk.hash, chunk.size, 1)
                    )
                    if is_new:
                        new_chunk_count += 1
                else:
                    cursor.execute(
                        "UPDATE chunks SET ref_count = ref_count + 1 WHERE hash = ?",
                        (chunk.hash,)
                    )

            conn.commit()

        self._auto_backup_db()
        return new_chunk_count

    def store_manifest(self, manifest: Manifest) -> None:
        """
        Saves a Manifest object into SQLite.
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO manifests (snapshot_id, original_path, data, created_at) VALUES (?, ?, ?, ?)",
                (
                    manifest.snapshot_id,
                    manifest.original_path,
                    manifest.to_json(),
                    manifest.created_at
                )
            )
            conn.commit()
        
        self._auto_backup_db()

    def get_chunk_data(self, hash_digest: str) -> bytes:
        """
        Retrieves chunk bytes from disk. Decompresses zstd data or falls back to raw bytes.
        """
        subdir = os.path.join(self.chunks_dir, hash_digest[:2], hash_digest[2:4])
        chunk_file_path = os.path.join(subdir, hash_digest)

        if not os.path.exists(chunk_file_path):
            raise FileNotFoundError(f"Chunk file not found in vault: {hash_digest}")

        with open(chunk_file_path, "rb") as f:
            raw_file_bytes = f.read()

        try:
            return self.decompressor.decompress(raw_file_bytes)
        except zstd.ZstdError:
            return raw_file_bytes

    def get_manifest(self, snapshot_id: str) -> Optional[Manifest]:
        """
        Fetches and returns a Manifest object from SQLite using snapshot_id.
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT data FROM manifests WHERE snapshot_id = ?", (snapshot_id,))
            row = cursor.fetchone()

            if row is None:
                return None

            return Manifest.from_json(row[0])

    def get_all_manifests(self) -> List[Manifest]:
        """
        Retrieves all stored manifests from the SQLite database.
        """
        manifests = []
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT data FROM manifests ORDER BY created_at DESC")
            rows = cursor.fetchall()
            for row in rows:
                manifests.append(Manifest.from_json(row[0]))
        return manifests
