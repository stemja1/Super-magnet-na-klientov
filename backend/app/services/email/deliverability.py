"""Email deliverability checker: SPF / DKIM / DMARC analyzer (spec §3).

Best-effort DNS TXT lookup via `dig` (or `dns.resolver` if installed). When no
DNS tooling is available (CI/offline) it reports "unchecked" rather than failing.
"""
from __future__ import annotations

import re
import subprocess


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
        # Fallback to dig CLI.
        try:
            out = subprocess.run(
                ["dig", "+short", "TXT", host],
                capture_output=True,
                text=True,
                timeout=5,
            )
            return out.stdout.strip()
        except Exception:
            return None

    def check(self, domain: str) -> dict:
        spf = self._txt(domain) or self._txt(f"_spf.{domain}")
        dmarc = self._txt(f"_dmarc.{domain}")
        dkim = self._txt(f"default._domainkey.{domain}")

        issues: List[str] = []
        if not spf or "v=spf1" not in spf:
            issues.append("Chýba alebo neplatný SPF záznam")
        if not dmarc or "v=DMARC1" not in dmarc:
            issues.append("Chýba DMARC záznam")
        if not dkim:
            issues.append("Nezistený DKIM (skontrolujte selector domény)")

        score = max(0, 100 - 34 * len(issues))
        checked = bool(spf or dmarc or dkim)
        return {
            "domain": domain,
            "spf": bool(spf and "v=spf1" in spf),
            "dmarc": bool(dmarc and "v=DMARC1" in dmarc),
            "dkim_found": bool(dkim),
            "score": score,
            "issues": issues,
            "mode": "checked" if checked else "unchecked",
        }
