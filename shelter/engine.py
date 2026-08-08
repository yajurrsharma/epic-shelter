import os
import time
import uuid
from typing import List
from models import Manifest, Chunk
from vault import Vault
from chunker import stream_chunks

class BackupEngine:
    
    """
    The BackupEngine orchestrates the backup process, including chunking files,
    storing chunks in the vault, and creating manifests for each backup snapshot.
    """

    def __init__(self, vault_path: str = ".shelter"):
        self.vault = Vault(vault_path)

    def backup_file(self, file_path: str) -> Manifest:

        """
        Processes a file: streams chunks through FastCDC, deduplicates them in the vault,
        and generates an ordered manifest snapshot.
        """

        abs_path = os.path.abspath(file_path)
        if not os.path.exists(abs_path):
            raise FileNotFoundError(f"File not found: {abs_path}")

        snapshot_id = str(uuid.uuid4())[:8]
        chunk_hashes = []
        chunks_batch: List[Chunk] = []
        
        total_file_size = 0

        for chunk in stream_chunks(abs_path):
            total_file_size += chunk.size
            chunk_hashes.append(chunk.hash)
            chunks_batch.append(chunk)

        self.vault.store_chunks_batch(chunks_batch)

        manifest = Manifest(
            snapshot_id=snapshot_id,
            original_path=abs_path,
            file_size=total_file_size,
            chunk_hashes=chunk_hashes,
            created_at=time.time()
        )

        self.vault.store_manifest(manifest)

        return manifest

    def restore_file(self, snapshot_id: str, output_path: str) -> str:

        """
        Rebuilds a file bit-for-bit using a snapshot_id and writes it to output_path.
        """
        
        manifest = self.vault.get_manifest(snapshot_id)
        if not manifest:
            raise ValueError(f"Snapshot ID not found in vault: {snapshot_id}")

        abs_output_path = os.path.abspath(output_path)
        output_dir = os.path.dirname(abs_output_path)
        if output_dir:
            os.makedirs(output_dir, exist_ok=True)

        with open(abs_output_path, "wb") as f:
            for hash_digest in manifest.chunk_hashes:
                chunk_bytes = self.vault.get_chunk_data(hash_digest)
                f.write(chunk_bytes)

        return abs_output_path