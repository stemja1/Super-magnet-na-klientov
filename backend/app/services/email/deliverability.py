"""Email deliverability checker: SPF / DKIM / DMARC analyzer (spec §3).

Best-effort DNS TXT lookup via `dns.resolver` (dnspython) when installed, else the
`dig` CLI. When no DNS tooling is available (CI / offline / Windows without
dnspython) the check reports ``mode: "unchecked"`` instead of failing.
"""
from __future__ import annotations

import logging
import shutil
import subprocess
from typing import List, Optional

logger = logging.getLogger("deliverability")


class DeliverabilityChecker:
    def _txt(self, host: str) -> Optional[str]:
        # Prefer dnspython if present.
        try:
            import dns.resolver  # type: ignore

            answers = dns.resolver.resolve(host, "TXT")
            return "\n".join(
                "".join(str(s) for s in r.strings) for r in answers
            )
        except Exception:
            pass
        # Fallback to the dig CLI when it is installed.
        dig = shutil.which("dig")
        if not dig:
            return None
        try:
            out = subprocess.run(
                [dig, "+short", "TXT", host],
                capture_output=True,
                text=True,
                timeout=5,
            )
            return out.stdout.strip() or None
        except Exception:
            return None

    def check(self, domain: str) -> dict:
        # SPF lives in a TXT record on the domain apex.
        spf_txt = self._txt(domain)
        dmarc_txt = self._txt(f"_dmarc.{domain}")
        # DKIM selectors are per-mailbox; "default"/"selector1"/"selector2" cover
        # the overwhelming majority of setups (Google Workspace, Mailgun, SES).
        dkim_txt = None
        dkim_selector = None
        for selector in ("default", "selector1", "selector2"):
            txt = self._txt(f"{selector}._domainkey.{domain}")
            if txt and "p=" in txt:
                dkim_txt, dkim_selector = txt, selector
                break

        spf_ok = bool(spf_txt and "v=spf1" in spf_txt)
        dmarc_ok = bool(dmarc_txt and "v=DMARC1" in dmarc_txt)
        dkim_ok = dkim_txt is not None

        issues: List[str] = []
        if not spf_ok:
            issues.append("Chýba alebo neplatný SPF záznam")
        if not dmarc_ok:
            issues.append("Chýba DMARC záznam")
        if not dkim_ok:
            issues.append("Nezistený DKIM (skontrolujte selector domény)")

        checked = bool(spf_txt or dmarc_txt or dkim_txt)
        score = max(0, 100 - 34 * len(issues)) if checked else 0
        return {
            "domain": domain,
            "spf": spf_ok,
            "dmarc": dmarc_ok,
            "dkim_found": dkim_ok,
            "dkim_selector": dkim_selector,
            "score": score,
            "issues": issues,
            "mode": "checked" if checked else "unchecked",
        }
