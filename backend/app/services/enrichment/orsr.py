"""ORSR connector — Slovak business registry (or.sr / orsr.sk).

Design (spec §10): use only public interfaces, never scrape behind a login wall.
The connector is **graceful**: with ``ORSR_MOCK=1`` (tests / offline) it returns
deterministic demo profiles so the pipeline stays runnable without network. The
live path does a best-effort HTTP lookup via urllib (no extra dependency) and
falls back on any error.

Known limitation: or.sr has no public API, so name extraction is heuristic and
cached per process to avoid hammering the site during bulk imports.
"""
from __future__ import annotations

import logging
import os
import re
import threading
import urllib.parse
import urllib.request
from dataclasses import dataclass

logger = logging.getLogger("orsr")

LOOKUP_URL = "https://or.sr/index.jsp?"
TIMEOUT_SECONDS = 10
MAX_CACHE_ENTRIES = 2048


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
        self._cache: dict[str, CompanyProfile] = {}
        self._lock = threading.Lock()

    def get_by_ico(self, ico: str) -> CompanyProfile:
        ico = (ico or "").strip()
        if not ico:
            return CompanyProfile(name="", ico="", status="Chýba IČO")
        if self.mock:
            return CompanyProfile(
                name=f"Demo firma ({ico}) s.r.o.",
                ico=ico,
                address="Bratislava, Slovensko",
                legal_form="s.r.o.",
                status="Platný",
            )
        with self._lock:
            cached = self._cache.get(ico)
        if cached is not None:
            return cached
        try:
            profile = self._fetch(ico)
        except Exception as exc:  # pragma: no cover - network dependent
            logger.warning("ORSR fetch failed for %s: %s", ico, exc)
            profile = CompanyProfile(name=f"Firma {ico}", ico=ico, status="ORSR nedostupné")
        with self._lock:
            if len(self._cache) >= MAX_CACHE_ENTRIES:
                self._cache.clear()
            self._cache[ico] = profile
        return profile

    def _fetch(self, ico: str) -> CompanyProfile:
        url = LOOKUP_URL + urllib.parse.urlencode(
            {"lan": "sk", "p": "1", "r": "1", "ICO": ico}
        )
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=TIMEOUT_SECONDS) as resp:
            html = resp.read().decode("utf-8", "ignore")
        name = self._parse_name(html)
        return CompanyProfile(
            name=name or f"Firma {ico}",
            ico=ico,
            legal_form=self._parse_legal_form(name) if name else "",
            status="Načítané z ORSR" if name else "Názov sa nepodarilo načítať",
        )

    # Legal forms seen in the Slovak register, in both spaced and compact
    # spelling. Ordered longest-first when building the regex so "s. r. o." wins
    # over a shorter overlapping alternative.
    _LEGAL_FORMS = (
        "spol. s. r. o.", "spol. s r.o.", "s. r. o.", "s.r.o.",
        "k. č. s.", "k. č. s", "v. o. s.", "e. k.",
        "a. s.", "a.s.", "k. s.", "š. p.", "š.p.",
        "SZČO", "SZČO s.r.o.", "S.Ž.", "S. Ž.",
        "družstvo", "nadácia", "ústav", "fyzická osoba",
    )

    @staticmethod
    def _parse_name(html: str) -> str | None:
        """Extract the trade name following an 'Obchodné meno' label.

        Accepts every Slovak legal form, not just s.r.o. — the previous pattern
        silently returned nothing for a.s., SZČO and k.č. companies.
        """
        forms = "|".join(
            re.escape(f) for f in sorted(OrsrConnector._LEGAL_FORMS, key=len, reverse=True)
        )
        pattern = (
            r"Obchodn[ée]\s*meno.{0,200}?([A-ZÁÄČĎÉÍĹĽŇÓÔŔŠŤÚÝŽ0-9][^<>{}]{2,90}?"
            rf"(?:{forms}))"
        )
        m = re.search(pattern, html, re.IGNORECASE | re.DOTALL)
        if not m:
            return None
        name = " ".join(m.group(1).split()).strip(" -–—:;,")
        return name or None

    @staticmethod
    def _parse_legal_form(name: str | None) -> str:
        if not name:
            return ""
        low = name.lower()
        # Longest first so "s. r. o." is reported instead of a nested "o." match.
        for form in sorted(OrsrConnector._LEGAL_FORMS, key=len, reverse=True):
            if form.lower() in low:
                return form
        return ""


# Module-level singleton used by the leads service.
orsr = OrsrConnector()
