import os
import xxhash
from typing import Generator
from models import Chunk

MIN_CHUNK_SIZE = 512 * 1024 # 512 KN
TARGET_CHUNK_SIZE = 2 * 1024 * 1024 # 2MB
MAX_CHUNK_SIZE = 8 * 1024 * 1024 #8MB

MASK_STRICT = 0x0001FFFF 
MASK_LOOSE = 0x00007FFF  

GEAR_TABLE = [
    ((i * 2654435761) & 0xFFFFFFFF) for i in range(256)
]


"""

FOLLOWED GUIDE FROM https://joshleeb.com/posts/gearhash.html
FOR GEAR HASHING AND FASTCDC

"""

def stream_chunks(file_path: str) -> Generator[Chunk, None, None]:

    """
    Streams chunks of data from a file using FastCDC and xxhash (XXH3_64).
    Processes files cleanly to EOF without memory ballooning.
    """

    if not os.path.exists(file_path):
        raise FileNotFoundError(f"File not found: {file_path}")

    buffer = bytearray()
    read_block_size = 4 * 1024 * 1024  # 4 MB read window
    offset = 0

    with open(file_path, "rb") as f:
        while True:
            if len(buffer) < MAX_CHUNK_SIZE:
                more_bytes = f.read(read_block_size)
                if more_bytes:
                    buffer.extend(more_bytes)

            if not buffer:
                break

            buffer_length = len(buffer)

            if buffer_length <= MIN_CHUNK_SIZE:
                chunk_data = bytes(buffer)
                chunk_hash = xxhash.xxh3_64_hexdigest(chunk_data)
                yield Chunk(
                    hash=chunk_hash,
                    size=len(chunk_data),
                    offset=offset,
                    data=chunk_data
                )
                buffer.clear()
                break

            cut_point = MIN_CHUNK_SIZE
            fingerprint = 0
            max_scan = min(buffer_length, MAX_CHUNK_SIZE)

            while cut_point < max_scan:
                byte_val = buffer[cut_point]
                fingerprint = ((fingerprint << 1) + GEAR_TABLE[byte_val]) & 0xFFFFFFFF
                mask = MASK_STRICT if cut_point < TARGET_CHUNK_SIZE else MASK_LOOSE

                if (fingerprint & mask) == 0:
                    break

                cut_point += 1

            chunk_bytes = bytes(buffer[:cut_point])
            del buffer[:cut_point]

            chunk_hash = xxhash.xxh3_64_hexdigest(chunk_bytes)

            yield Chunk(
                hash=chunk_hash,
                size=len(chunk_bytes),
                offset=offset,
                data=chunk_bytes
            )

            offset += len(chunk_bytes)
