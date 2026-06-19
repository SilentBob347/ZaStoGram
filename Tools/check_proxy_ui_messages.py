#!/usr/bin/env python3
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]

STRINGS = ROOT / "TMessagesProj/src/main/res/values/strings.xml"
PROXY_LIST = ROOT / "TMessagesProj/src/main/java/org/telegram/ui/ProxyListActivity.java"
PROXY_SETTINGS = ROOT / "TMessagesProj/src/main/java/org/telegram/ui/ProxySettingsActivity.java"

checks = [
    (STRINGS, 'name="ProxyStatusConnectingSlow"', "missing slow connecting proxy status string"),
    (STRINGS, 'name="ProxyStatusCheckingConnection"', "missing proxy checking status string"),
    (STRINGS, 'name="ProxyStatusNotRespondingNow"', "missing temporary proxy failure string"),
    (STRINGS, 'name="UseProxyTelegramInfoStealth"', "missing MTProto stealth hint string"),
    (PROXY_LIST, "R.string.ProxyStatusConnectingSlow", "proxy list does not use slow connecting text"),
    (PROXY_LIST, "R.string.ProxyStatusCheckingConnection", "proxy list does not use checking text"),
    (PROXY_LIST, "R.string.ProxyStatusNotRespondingNow", "proxy list does not use neutral MTProto failure text"),
    (PROXY_LIST, "TextUtils.isEmpty(currentInfo.secret)", "proxy list does not distinguish MTProto from SOCKS failures"),
    (PROXY_SETTINGS, "R.string.UseProxyTelegramInfoStealth", "proxy settings does not show MTProto stealth hint"),
]

failed = []
for path, needle, message in checks:
    text = path.read_text(encoding="utf-8")
    if needle not in text:
        failed.append(f"{path.relative_to(ROOT)}: {message}")

if failed:
    print("Proxy UI message guard failed:")
    for item in failed:
        print(f" - {item}")
    sys.exit(1)

print("Proxy UI message guard passed.")
