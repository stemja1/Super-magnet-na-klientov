"""ORSR connector — Slovak business registry (or.sr / orsr.sk).

Design (spec §10): use only official/public interfaces; never scrape behind
login walls. This connector is **graceful**: when ``ORSR_MOCK=1`` (default in
tests/offline) it returns deterministic demo profiles so the pipeline is fully
runnable without network. The real path does a best-effort HTTP lookup via
urllib (no extra dependency) and falls back on any error.
"""
from __future__ import annotations

import logging
import os
import re
import urllib.parse
import urllib.request
from dataclasses import dataclass

logger = logging.getLogger("orsr")


@dataclass
class CompanyProfile:
    name: str
    ico: str
    address: str = ""
    legal_form: str = ""
    status: str = ""


class OrsrConnector:
    def __init__(self, mock: bool | None = None) -> None:
        self.mock = mock if mock is not None else os.getenv("ORSR_MOCK", "0") == "1"

    def get_by_ico(self, ico: str) -> CompanyProfile:
        ico = (ico or "").strip()
        if self.mock:
            return CompanyProfile(
                name=f"Demo firma ({ico}) s.r.o.",
                ico=ico,
                address="Bratislava, Slovensko",
                legal_form="s.r.o.",
                status="Platný",
            )
        try:
            return self._fetch(ico)
        except Exception as exc:  # pragma: no cover - network dependent
            logger.warning("ORSR fetch failed for %s: %s", ico, exc)
            return CompanyProfile(name=f"Firma {ico}", ico=ico, status="ORSR nedostupné")

    def _fetch(self, ico: str) -> CompanyProfile:
        url = "https://or.sr/index.jsp?" + urllib.parse.urlencode(
            {"lan": "sk", "p": "1", "r": "1", "ICO": ico}
        )
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            html = resp.read().decode("utf-8", "ignore")
        name = self._parse_name(html) or f"Firma {ico}"
        return CompanyProfile(name=name, ico=ico, status="Načítané z ORSR")

    @staticmethod
    def _parse_name(html: str) -> str | None:
        m = re.search(r"Obchodn[ée]\s*meno[^\n]{0,200}?([A-ZÁ-Ž][\w\s\.\,\-]{3,80}?s\.r\.o\.)", html)
        if m:
            return m.group(1).strip()
        return None


# Module-level singleton used by the leads service.
orsr = OrsrConnector()
