#!/usr/bin/env python3
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]

SCHEDULER = ROOT / "TMessagesProj/src/main/java/org/telegram/messenger/ProxyCheckScheduler.java"
PROXY_LIST = ROOT / "TMessagesProj/src/main/java/org/telegram/ui/ProxyListActivity.java"
ROTATION = ROOT / "TMessagesProj/src/main/java/org/telegram/messenger/ProxyRotationController.java"

checks = [
    (SCHEDULER, "PROXY_CHECK_SPACING_MS", "scheduler must space background proxy checks"),
    (SCHEDULER, "activeRequest", "scheduler must keep a single active background check"),
    (SCHEDULER, "enqueueStale", "scheduler must expose stale-check enqueueing"),
    (SCHEDULER, "cancelOwner", "scheduler must let screens cancel queued checks"),
    (SCHEDULER, "onProxyCheckQueueFinished", "scheduler must notify owners when their sweep is drained"),
    (PROXY_LIST, "ProxyCheckScheduler.enqueueStale", "proxy list must use the shared scheduler"),
    (PROXY_LIST, "ProxyCheckScheduler.cancelOwner(this)", "proxy list must cancel queued checks on destroy"),
    (ROTATION, "ProxyCheckScheduler.enqueueStale", "proxy rotation must use the shared scheduler"),
    (ROTATION, "onProxyCheckQueueFinished", "proxy rotation must wait for the scheduler drain signal"),
]

failed = []
for path, needle, message in checks:
    if not path.exists():
        failed.append(f"{path.relative_to(ROOT)}: missing file")
        continue
    text = path.read_text(encoding="utf-8")
    if needle not in text:
        failed.append(f"{path.relative_to(ROOT)}: {message}")

if failed:
    print("Proxy check scheduler guard failed:")
    for item in failed:
        print(f" - {item}")
    sys.exit(1)

print("Proxy check scheduler guard passed.")
