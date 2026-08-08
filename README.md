# EpicShelter

> **Content-Addressed Storage Engine** <br>
> Created by Yajur Sharma — © EpicShelter 2026

`EpicShelter` is a lightweight, high-performance CLI backup engine built on FastCDC variable-size chunking, content-addressed storage (CAS), and SQLite metadata tracking with automatic Zstandard compression.

---

## Key Features

- **Content-Addressed Deduplication:** Breaks files down into content-defined chunks (FastCDC) to eliminate duplicate storage across multiple snapshots.
- **Smart Zstandard Compression:** Automatically compresses data chunks using `zstd` level 1 for optimal speed and space saving.
- **ACID Metadata & Auto-Replication:** Uses SQLite WAL mode to log snapshots, automatically replicating metadata back to system user configuration directories (`~/.config/shelter/backups/`).
- **Cross-Platform Vault Concealment:** Automatically creates and hides `.shelter` storage repositories across Linux, macOS, and Windows.

---

## Installation

Install the latest version directly from PyPI:

    pip install epic-shelter

Or install the development version from GitHub:

    pip install git+https://github.com/yajurrsharma/epic-shelter.git

---

## Usage

Launch the interactive CLI shell from anywhere in your terminal:

    shelter
OR
```bash
python3 -m shelter
```

### Commands

Inside the `shelter` interactive shell:

- `manual` / `m` — Run in manual mode.
- `auto` / `automatic` / `a` — Run in automatic mode.
- `status` / `info` — Display vault status and path details.
- `help` / `?` — Show the help menu.
- `exit` / `quit` / `q` — Exit the shell.

---

## Architecture Overview

1. **Chunker (`chunker.py`):** Uses FastCDC gear-hash scanning with rolling window buffers and `xxhash` to split streams into content-defined chunks.
2. **Vault (`vault.py`):** Manages SQLite transactions for reference counting, snapshot manifests, and physical file storage in content-addressed directory trees.
3. **Engine (`engine.py`):** Orchestrates multi-threaded file traversal, chunking pipelines, and snapshot reconstruction.

---

## License

This project is licensed under the MIT License.
