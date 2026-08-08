from dataclasses import dataclass, field
import json
import time
from typing import List, Optional


"""

FOLLOWED GUIDE FROM https://joshleeb.com/posts/gearhash.html
FOR GEAR HASHING AND FASTCDC

"""

@dataclass(frozen=True)

class Chunk:

    """
    Represents an immutable single block of content-addressed data.
    """

    hash: str
    size: int
    offset: int
    data: Optional[bytes] = None    

    def is_loaded(self) -> bool:
        """
        Returns True if the chunk's data is loaded in memory, False otherwise.
        """
        return self.data is not None


@dataclass(frozen=True)
class Manifest:
    """
    Represents a point in time file backup framework
    """

    snapshot_id: str
    original_path: str
    file_size: int
    chunk_hashes: List[str] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)

    def to_json(self) -> str:
        """
        Serializes the Manifest instance to a JSON string.
        """
        return json.dumps({
            "snapshot_id": self.snapshot_id,
            "original_path": self.original_path,
            "file_size": self.file_size,
            "chunk_hashes": self.chunk_hashes,
            "created_at": self.created_at
        })

    @classmethod
    def from_json(cls, json_str: str) -> 'Manifest':
        """
        Deserializes a JSON string to a Manifest instance.
        """
        data = json.loads(json_str)
        return cls(
            snapshot_id=data["snapshot_id"],
            original_path=data["original_path"],
            file_size=data["file_size"],
            chunk_hashes=data["chunk_hashes"],
            created_at=data.get("created_at", time.time())
        )   