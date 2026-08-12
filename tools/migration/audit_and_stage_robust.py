#!/usr/bin/env python3
"""Robust network wrapper for audit_and_stage.py.

Keeps the original audit logic unchanged but replaces its download() function
with a resumable/retrying implementation suitable for unstable GitHub release
connections.

SAFE MODE: same safety guarantees as audit_and_stage.py.
"""
from __future__ import annotations

import re
import time
import urllib.request
from pathlib import Path

import audit_and_stage as base

MAX_ATTEMPTS = 6
BASE_WAIT_SECONDS = 3
TIMEOUT_SECONDS = 180


def _expected_total(response, existing: int) -> int:
    content_range = response.headers.get("Content-Range", "")
    match = re.search(r"/(\d+)$", content_range)
    if match:
        return int(match.group(1))
    length = int(response.headers.get("Content-Length", "0") or 0)
    status = getattr(response, "status", None) or response.getcode()
    if status == 206:
        return existing + length
    return length


def robust_download(url: str, dst: Path) -> None:
    expected = base.EXPECTED_SHA256.get(dst.name)

    if dst.exists():
        actual = base.sha256_file(dst)
        if expected and actual.lower() == expected.lower():
            print(f"[OK] Reusing verified {dst.name}")
            return
        print(f"[WARN] Existing {dst.name} hash mismatch; removing it")
        dst.unlink(missing_ok=True)

    tmp = dst.with_suffix(dst.suffix + ".part")
    last_error = None

    print(f"[DOWNLOAD] {dst.name} (robust mode)")

    for attempt in range(1, MAX_ATTEMPTS + 1):
        existing = tmp.stat().st_size if tmp.exists() else 0
        headers = {
            "User-Agent": "XMage-Community-Patch-Migration-Audit/2.2",
            "Accept": "application/octet-stream",
            "Connection": "close",
        }
        if existing:
            headers["Range"] = f"bytes={existing}-"
            print(f"[RETRY {attempt}/{MAX_ATTEMPTS}] resuming from {existing / (1024*1024):.1f} MiB")
        else:
            print(f"[TRY {attempt}/{MAX_ATTEMPTS}] starting download")

        try:
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=TIMEOUT_SECONDS) as response:
                status = getattr(response, "status", None) or response.getcode()

                # If server ignored Range, restart the partial file safely.
                if existing and status != 206:
                    print("[INFO] Server did not accept resume; restarting this file")
                    existing = 0
                    mode = "wb"
                else:
                    mode = "ab" if existing else "wb"

                total = _expected_total(response, existing)
                done = existing
                last_pct = -1

                with tmp.open(mode) as out:
                    while True:
                        data = response.read(base.CHUNK)
                        if not data:
                            break
                        out.write(data)
                        done += len(data)
                        if total:
                            pct = int(done * 100 / total)
                            if pct != last_pct and (pct % 5 == 0 or pct == 100):
                                print(f"  {pct}%")
                                last_pct = pct

            if total and tmp.stat().st_size != total:
                raise RuntimeError(
                    f"Incomplete download for {dst.name}: "
                    f"{tmp.stat().st_size} of {total} bytes"
                )

            actual = base.sha256_file(tmp)
            if expected and actual.lower() != expected.lower():
                # A resumed file with a bad hash is not trustworthy. Restart clean.
                tmp.unlink(missing_ok=True)
                raise RuntimeError(f"SHA-256 mismatch for {dst.name}: {actual}")

            tmp.replace(dst)
            print(f"[OK] SHA-256 verified: {dst.name}")
            return

        except Exception as exc:
            last_error = exc
            print(f"[WARN] Attempt {attempt}/{MAX_ATTEMPTS} failed: {exc}")
            if attempt < MAX_ATTEMPTS:
                wait = BASE_WAIT_SECONDS * attempt
                print(f"[WAIT] retrying in {wait} seconds...")
                time.sleep(wait)

    raise RuntimeError(
        f"Download failed after {MAX_ATTEMPTS} attempts for {dst.name}: {last_error}"
    )


def main() -> int:
    base.download = robust_download
    print("=== NETWORK HARDENING ACTIVE: retry + resume + SHA-256 ===")
    return base.main()


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        print("\nCancelled. Active XMage was not modified.")
        raise SystemExit(130)
    except Exception as exc:
        print(f"\nERROR: {exc}")
        print("Active XMage was not modified.")
        input("Press Enter to close...")
        raise SystemExit(1)
