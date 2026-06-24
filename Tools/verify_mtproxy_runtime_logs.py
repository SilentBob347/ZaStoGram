#!/usr/bin/env python3
"""Verify live MTProxy runtime log evidence after an APK/logcat capture.

This is intentionally stricter than the human-facing analyzer. It answers the
post-build question from the transport-state hardening work: did the live log
actually contain the new state fields and the split endpoint-success markers?
"""

from __future__ import annotations

import argparse
import re
from pathlib import Path


REASON_RE = re.compile(r"(?<![A-Za-z0-9_])reason=([^ ]+)")
CONNECTION_RE = re.compile(r"connection\((0x[0-9a-fA-F]+)\)")
DISCONNECT_REQUIRED_FIELDS = (
    "transport_state=",
    "epoll_registered=",
    "admission_active=",
    "tcp_gate_active=",
)
ALLOWED_DATA_PATH_REASONS = {"first_tls_app_recv", "first_mtproxy_packet_recv"}


def resolve_markers_path(path: Path) -> Path:
    if path.is_dir():
        marker_path = path / "mtproxy_markers.txt"
    else:
        marker_path = path
    if not marker_path.exists():
        raise SystemExit(f"markers file not found: {marker_path}")
    return marker_path


def read_lines(path: Path) -> list[str]:
    return path.read_text(encoding="utf-8", errors="replace").splitlines()


def line_reason(line: str) -> str:
    match = REASON_RE.search(line)
    return match.group(1) if match else ""


def line_connection(line: str) -> str:
    match = CONNECTION_RE.search(line)
    return match.group(1) if match else ""


def has_prior_connection_marker(lines: list[str], index: int, connection: str, marker: str) -> bool:
    for candidate in lines[:index]:
        if marker not in candidate:
            continue
        if connection and line_connection(candidate) != connection:
            continue
        return True
    return False


def verify_lines(lines: list[str]) -> list[str]:
    failures: list[str] = []
    transport_state_lines = [line for line in lines if "transport_state=" in line]
    handshake_lines = [line for line in lines if "endpoint_handshake_ok" in line]
    data_path_lines = [line for line in lines if "endpoint_data_path_success" in line]
    server_hello_lines = [line for line in lines if "server_hello_hmac_ok" in line]
    disconnect_lines = [line for line in lines if "mtproxy_disconnect" in line]

    if not transport_state_lines:
        failures.append("missing transport_state= evidence in runtime logs")
    if not handshake_lines:
        failures.append("missing endpoint_handshake_ok marker in runtime logs")
    if not data_path_lines:
        failures.append("missing endpoint_data_path_success marker in runtime logs")

    if server_hello_lines and not any(line_reason(line) == "server_hello_hmac_ok" for line in handshake_lines):
        failures.append("server_hello_hmac_ok must produce endpoint_handshake_ok reason=server_hello_hmac_ok")

    for line in handshake_lines:
        reason = line_reason(line)
        if reason and reason != "server_hello_hmac_ok":
            failures.append(f"endpoint_handshake_ok must use reason=server_hello_hmac_ok: {line}")

    for index, line in enumerate(lines):
        if "endpoint_data_path_success" not in line:
            continue
        reason = line_reason(line)
        if reason == "server_hello_hmac_ok":
            failures.append("endpoint_data_path_success must not use reason=server_hello_hmac_ok")
        elif reason not in ALLOWED_DATA_PATH_REASONS:
            failures.append(
                "endpoint_data_path_success must use reason=first_tls_app_recv "
                f"or first_mtproxy_packet_recv: {line}"
            )
        elif not has_prior_connection_marker(lines, index, line_connection(line), f"mtproxy_startup {reason}"):
            failures.append(
                f"endpoint_data_path_success reason={reason} must be preceded by {reason} "
                f"app-data marker on the same connection: {line}"
            )

    for line in disconnect_lines:
        missing = [field for field in DISCONNECT_REQUIRED_FIELDS if field not in line]
        if missing:
            failures.append(f"mtproxy_disconnect missing invariant fields {','.join(missing)}: {line}")

    return failures


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "path",
        type=Path,
        help="Path to a collect_mtproxy_logs session directory or mtproxy_markers.txt",
    )
    args = parser.parse_args()

    marker_path = resolve_markers_path(args.path)
    failures = verify_lines(read_lines(marker_path))
    if failures:
        print("MTProxy runtime log contract failed:", file=__import__("sys").stderr)
        for failure in failures:
            print(f" - {failure}", file=__import__("sys").stderr)
        return 1

    print("MTProxy runtime log contract passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
