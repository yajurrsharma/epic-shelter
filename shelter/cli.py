import os
import sys
import secrets
import time
from typing import List
from shelter.engine import BackupEngine
from shelter.vault import Vault

"""

FOLLOWED GUIDE FROM https://joshleeb.com/posts/gearhash.html
FOR GEAR HASHING AND FASTCDC

"""

CYAN = "\033[96m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
MAGENTA = "\033[95m"
RED = "\033[91m"
BOLD = "\033[1m"
RESET = "\033[0m"

ASCII_BANNER = r"""
   ▄████████    ▄███████▄  ▄█   ▄████████    ▄████████    ▄█    █▄       ▄████████  ▄█           ███        ▄████████    ▄████████ 
  ███    ███   ███    ███ ███  ███    ███   ███    ███   ███    ███     ███    ███ ███       ▀█████████▄   ███    ███   ███    ███ 
  ███    █▀    ███    ███ ███▌ ███    █▀    ███    █▀    ███    ███     ███    █▀  ███          ▀███▀▀██   ███    █▀    ███    ███ 
 ▄███▄▄▄       ███    ███ ███▌ ███          ███         ▄███▄▄▄▄███▄▄  ▄███▄▄▄     ███           ███   ▀  ▄███▄▄▄      ▄███▄▄▄▄██▀ 
▀▀███▀▀▀     ▀█████████▀  ███▌ ███        ▀███████████ ▀▀███▀▀▀▀███▀  ▀▀███▀▀▀     ███           ███     ▀▀███▀▀▀     ▀▀███▀▀▀▀▀   
  ███    █▄    ███        ███  ███    █▄           ███   ███    ███     ███    █▄  ███           ███       ███    █▄  ▀███████████ 
  ███    ███   ███        ███  ███    ███    ▄█    ███   ███    ███     ███    ███ ███▌    ▄     ███       ███    ███   ███    ███ 
  ██████████  ▄████▀      █▀   ████████▀   ▄████████▀    ███    █▀      ██████████ █████▄▄██    ▄████▀     ██████████   ███    ███ 

  
               Content-Addressed Storage Engine


    Created by Yajur Sharma 

    © 2026 EpicShelter. Licensed under the MIT License.                
"""

CURRENT_OTP = ""
IS_NEWLY_GENERATED = False


def format_elapsed_time(seconds: float) -> str:
    """Formats raw seconds into readable time"""
    if seconds < 0.01:
        return f"{seconds * 1000:.1f}ms"
    return f"{seconds:.2f}s"


def load_or_create_otp(vault: Vault):
    """
    Loads persistent OTP, if no OTP exists, creates one and flags it as newly generated
    """
    global CURRENT_OTP, IS_NEWLY_GENERATED
    existing_otp = vault.get_config("otp")
    revealed_flag = vault.get_config("otp_revealed")

    if existing_otp:
        CURRENT_OTP = existing_otp
        IS_NEWLY_GENERATED = (revealed_flag == "0")
    else:
        CURRENT_OTP = secrets.token_hex(3).upper()
        vault.set_config("otp", CURRENT_OTP)
        vault.set_config("otp_revealed", "0")
        IS_NEWLY_GENERATED = True


def regenerate_and_display_new_otp(vault: Vault) -> str:
    """
    Burns current OTP, generates a fresh one, and prints single-time display warning
    """
    global CURRENT_OTP, IS_NEWLY_GENERATED
    CURRENT_OTP = secrets.token_hex(3).upper()
    vault.set_config("otp", CURRENT_OTP)
    vault.set_config("otp_revealed", "0")
    IS_NEWLY_GENERATED = True

    print(f"\n{BOLD}{RED}================================================================={RESET}")
    print(f"{BOLD}{RED} ONE-TIME PASSKEY GENERATED: {YELLOW}{CURRENT_OTP}{RESET}")
    print(f"{BOLD}{RED} WARNING: WRITE THIS DOWN NOW! IT WILL NEVER BE SHOWN AGAIN.{RESET}")
    print(f"{BOLD}{RED} WITHOUT THIS PASSKEY YOU WILL NOT BE ABLE TO RECOVER FILES.{RESET}")
    print(f"{BOLD}{RED}================================================================={RESET}\n")

    vault.set_config("otp_revealed", "1")
    return CURRENT_OTP


def print_banner(vault: Vault):
    print(CYAN + ASCII_BANNER + RESET)
    print(f"\033[90m{'=' * 65}{RESET}")
    print(f" Type {BOLD}help{RESET} or {BOLD}?{RESET} to list available commands.")

    if IS_NEWLY_GENERATED:
        print(f" {BOLD}{RED} ONE-TIME PASSKEY:{RESET} {BOLD}{YELLOW}{CURRENT_OTP}{RESET}")
        print(f" {BOLD}{RED} IMPORTANT: WRITE IT DOWN NOW! IT WILL NEVER BE SHOWN AGAIN.{RESET}")
        print(f" {BOLD}{RED} WITHOUT IT, YOU WILL NOT BE ABLE TO RECOVER YOUR FILES.{RESET}")
        vault.set_config("otp_revealed", "1")

    print(f"\033[90m{'=' * 65}{RESET}\n")


def print_help():
    """Displays the main command menu."""
    print(f"\n{BOLD}[ AVAILABLE COMMANDS ]{RESET}")
    print(f"  {YELLOW}manual{RESET}    : Enter manual mode to backup or restore individual files.")
    print(f"  {YELLOW}auto{RESET}      : Enter automatic mode to recursively backup an entire directory.")
    print(f"  {YELLOW}status{RESET}    : Show current vault statistics, snapshot counts, and disk usage.")
    print(f"  {YELLOW}help{RESET}      : Display this help menu.")
    print(f"  {YELLOW}exit{RESET}      : Quit EpicShelter.\n")


def run_manual_mode(engine: BackupEngine):
    """
    Interactive text driven manual mode for single file operations
    """
    global CURRENT_OTP

    print(f"\n{BOLD}[ MANUAL MODE ]{RESET}")
    print(f"Commands: {YELLOW}backup{RESET} | {YELLOW}restore{RESET} | {YELLOW}back{RESET}")

    while True:
        try:
            cmd = input(f"shelter({MAGENTA}manual{RESET})> ").strip().lower()
        except (KeyboardInterrupt, EOFError):
            print("\nExiting...")
            sys.exit(0)

        if cmd in ("back", "exit", "quit"):
            break

        elif cmd == "backup":
            try:
                file_path = input("path > ").strip()
            except (KeyboardInterrupt, EOFError):
                print("\nExiting...")
                sys.exit(0)

            file_path = os.path.expanduser(file_path)

            if not file_path:
                print(f"{RED}[!] Path cannot be empty.{RESET}")
                continue

            if not os.path.exists(file_path) or os.path.isdir(file_path):
                print(f"{RED}[!] Error: Target file does not exist or is a directory.{RESET}")
                continue

            print(f"\n Backing up: {file_path}")
            try:
                start_time = time.perf_counter()
                manifest = engine.backup_file(file_path)
                elapsed_time = time.perf_counter() - start_time
                time_str = format_elapsed_time(elapsed_time)

                print(f"{GREEN}[✓] Backup Successful! (took {time_str}){RESET}")
                print(f"  • Snapshot ID : {BOLD}{manifest.snapshot_id}{RESET}")
                print(f"  • File Size   : {manifest.file_size:,} bytes")
                print(f"  • Total Chunks: {len(manifest.chunk_hashes)}")
                print(f"  • Elapsed Time: {time_str}")
            except Exception as e:
                print(f"{RED}[!] Backup failed: {e}{RESET}")

        elif cmd == "restore":
            manifests = engine.vault.get_all_manifests()
            if not manifests:
                print(f"{YELLOW}[*] No backed-up files found in vault.{RESET}")
                continue

            print(f"\n{BOLD}[ STORED VAULT SNAPSHOTS ]{RESET}")
            print(f" {'#':<3} | {'Snapshot ID':<12} | {'Size':<10} | {'Original Path'}")
            print("-" * 65)

            for idx, m in enumerate(manifests, 1):
                size_str = f"{m.file_size / 1024:.1f} KB" if m.file_size < 1048576 else f"{m.file_size / 1048576:.1f} MB"
                print(f" {idx:<3} | {m.snapshot_id:<12} | {size_str:<10} | {m.original_path}")

            print(f"\n{BOLD}Selection Examples:{RESET} '1' (single file), '1, 3, 4' (multiple), or 'all'")

            try:
                selection = input(f"shelter({MAGENTA}manual/restore{RESET})> select #: ").strip().lower()
            except (KeyboardInterrupt, EOFError):
                print("\nExiting...")
                sys.exit(0)

            if not selection:
                print(f"{RED}[!] Selection cannot be empty.{RESET}")
                continue

            selected_manifests = []
            if selection == "all":
                selected_manifests = manifests
            else:
                try:
                    raw_indices = selection.replace(",", " ").split()
                    indices = [int(i) for i in raw_indices]
                    for i in indices:
                        if 1 <= i <= len(manifests):
                            selected_manifests.append(manifests[i - 1])
                        else:
                            print(f"{YELLOW}[*] Warning: #{i} out of range, skipping.{RESET}")
                except ValueError:
                    print(f"{RED}[!] Invalid selection format. Use numbers (e.g., 1 or 1,2,3).{RESET}")
                    continue

            if not selected_manifests:
                print(f"{RED}[!] No valid files selected.{RESET}")
                continue

            try:
                output_dir = input("destination folder > ").strip()
            except (KeyboardInterrupt, EOFError):
                print("\nExiting...")
                sys.exit(0)

            output_dir = os.path.expanduser(output_dir)
            if not output_dir:
                print(f"{RED}[!] Destination directory required.{RESET}")
                continue

            print(f"\n{BOLD}{RED}[ CONFIRMATION REQUIRED ]{RESET}")
            try:
                passkey_input = input("Enter One-Time Passkey > ").strip().upper()
            except (KeyboardInterrupt, EOFError):
                print("\nExiting...")
                sys.exit(0)

            active_token = CURRENT_OTP

            if passkey_input != active_token:
                print(f"\n{RED}[!] Access Denied: Incorrect One-Time Passkey.{RESET}")
                regenerate_and_display_new_otp(engine.vault)
                continue

            print(f"\n Restoring {len(selected_manifests)} file(s) to: {output_dir}\n")
            successful = 0
            failed = 0

            for m in selected_manifests:
                target_filename = os.path.basename(m.original_path)
                dest_path = os.path.join(output_dir, target_filename)

                try:
                    restored_file = engine.restore_file(m.snapshot_id, dest_path)
                    print(f" {GREEN}[✓] Restored:{RESET} {target_filename} -> {restored_file}")
                    successful += 1
                except Exception as e:
                    print(f" {RED}[!] Failed:{RESET} {target_filename} ({e})")
                    failed += 1

            print(f"\n{GREEN}[✓] Restore Process Completed! ({successful} success, {failed} failed){RESET}")
            
            regenerate_and_display_new_otp(engine.vault)

        elif cmd in ("help", "?"):
            print("  backup  - Interactively back up a single file.")
            print("  restore - Browse and select snapshot files to restore.")
            print("  back    - Return to main menu.")

        else:
            print(f"{RED}[!] Unknown command. Type 'backup', 'restore', or 'back'.{RESET}")


def run_automatic_mode(engine: BackupEngine):
    """
    Automatic mode: Scans a folder recursively and backs up all contained files
    """
    print(f"\n{BOLD}[ AUTOMATIC MODE - DIRECTORY BACKUP ]{RESET}")
    try:
        dir_path = input(f"shelter({YELLOW}auto{RESET})> path: ").strip()
    except (KeyboardInterrupt, EOFError):
        print("\nExiting...")
        sys.exit(0)

    dir_path = os.path.expanduser(dir_path)

    if not dir_path:
        print(f"{RED}[!] Path cannot be empty.{RESET}")
        return

    if not os.path.exists(dir_path) or not os.path.isdir(dir_path):
        print(f"{RED}[!] Error: Target directory does not exist.{RESET}")
        return

    files_to_backup: List[str] = []
    for root, _, files in os.walk(dir_path):
        for f in files:
            files_to_backup.append(os.path.join(root, f))

    total_files = len(files_to_backup)
    if total_files == 0:
        print(f"{YELLOW}[*] Directory is empty. Nothing to backup.{RESET}")
        return

    try:
        confirm = input(f"Discovered {total_files} file(s). Proceed with backup? (y/N): ").strip().lower()
    except (KeyboardInterrupt, EOFError):
        print("\nExiting...")
        sys.exit(0)

    if confirm != "y":
        print("[*] Operation cancelled.")
        return

    print(f"\n Running batch backup on {total_files} file(s)...\n")
    successful = 0
    failed = 0
    total_batch_start = time.perf_counter()

    for idx, fpath in enumerate(files_to_backup, 1):
        try:
            f_start = time.perf_counter()
            manifest = engine.backup_file(fpath)
            f_elapsed = time.perf_counter() - f_start
            time_str = format_elapsed_time(f_elapsed)

            print(f"[{idx}/{total_files}] {GREEN}[OK]{RESET} {fpath} -> Snapshot: {manifest.snapshot_id} ({time_str})")
            successful += 1
        except Exception as e:
            print(f"[{idx}/{total_files}] {RED}[FAIL]{RESET} {fpath} ({e})")
            failed += 1

    total_batch_elapsed = time.perf_counter() - total_batch_start
    total_time_str = format_elapsed_time(total_batch_elapsed)

    print(f"\n{GREEN}[✓] Batch Backup Complete! (took {total_time_str}){RESET}")
    print(f"  • Total Processed : {total_files}")
    print(f"  • Successful      : {successful}")
    print(f"  • Failed          : {failed}")
    print(f"  • Total Duration  : {total_time_str}")


def show_vault_status(vault_path: str):
    """
    Displays vault metrics.
    """
    if not os.path.exists(vault_path):
        print(f"{YELLOW}[*] Vault directory does not exist yet.{RESET}")
        return

    import sqlite3
    db_path = os.path.join(vault_path, "shelter.db")
    if not os.path.exists(db_path):
        print(f"{YELLOW}[*] Vault database not initialized.{RESET}")
        return

    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*), SUM(size) FROM chunks")
        chunk_count, total_chunk_bytes = cursor.fetchone()
        total_chunk_bytes = total_chunk_bytes or 0

        cursor.execute("SELECT COUNT(*) FROM manifests")
        manifest_count = cursor.fetchone()[0]

    print(f"\n{BOLD}[ VAULT STATUS ]{RESET}")
    print(f"  • Vault Location   : {os.path.abspath(vault_path)}")
    print(f"  • Total Snapshots  : {manifest_count}")
    print(f"  • Unique Chunks    : {chunk_count}")
    print(f"  • Storage Occupied : {total_chunk_bytes / (1024 * 1024):.2f} MB")


def main():
    vault_path = ".shelter"
    engine = BackupEngine(vault_path=vault_path)

    load_or_create_otp(engine.vault)
    print_banner(engine.vault)

    while True:
        try:
            cmd = input("shelter> ").strip().lower()
        except (KeyboardInterrupt, EOFError):
            print("\nExiting EpicShelter.")
            sys.exit(0)

        if not cmd:
            continue

        if cmd in ("manual", "m"):
            run_manual_mode(engine)

        elif cmd in ("auto", "automatic", "a"):
            run_automatic_mode(engine)

        elif cmd in ("status", "info"):
            show_vault_status(vault_path)

        elif cmd in ("help", "?"):
            print_help()

        elif cmd in ("exit", "quit", "q"):
            print("Exiting EpicShelter shell. Bye!")
            break

        else:
            print(f"{RED}[!] Unknown command: '{cmd}'. Type 'help' or '?' for available commands.{RESET}")


if __name__ == "__main__":
    main()
