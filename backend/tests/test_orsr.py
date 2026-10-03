from app.services.enrichment.orsr import OrsrConnector


def test_mock_profile_by_ico():
    conn = OrsrConnector(mock=True)
    prof = conn.get_by_ico("12345678")
    assert prof.ico == "12345678"
    assert prof.status == "Platný"
    assert "s.r.o." in prof.name


def test_real_connector_falls_back_gracefully():
    # With mock disabled but no network, connector must not raise.
    conn = OrsrConnector(mock=False)
    prof = conn.get_by_ico("00000000")
    assert prof.ico == "00000000"
    assert prof.name  # non-empty name (demo or fallback)


def test_empty_ico_is_rejected():
    conn = OrsrConnector(mock=False)
    prof = conn.get_by_ico("   ")
    assert prof.ico == ""
    assert prof.name == ""


def test_parses_sro_name():
    html = """
    <html><body>
      <div>Obchodné meno</div><div>Acme Slovakia s. r. o.</div>
      <div>IČO</div><div>12345678</div>
    </body></html>
    """
    assert OrsrConnector._parse_name(html) == "Acme Slovakia s. r. o."


def test_parses_non_sro_legal_forms():
    """Regression: the old regex required 's.r.o.' and matched nothing else."""
    cases = {
        "<div>Obchodné meno: Delta Holding a. s.</div>": "Delta Holding a. s.",
        "<div>Obchodné meno: Omega Stavby SZČO</div>": "Omega Stavby SZČO",
        "<div>Obchodné meno: Kapa Trade s.r.o.</div>": "Kapa Trade s.r.o.",
    }
    for html, expected in cases.items():
        assert OrsrConnector._parse_name(html) == expected, html


def test_returns_none_when_label_missing():
    assert OrsrConnector._parse_name("<div>Niečo iné</div>") is None


def test_detects_legal_form():
    assert OrsrConnector._parse_legal_form("Delta Holding a. s.") == "a. s."
    assert OrsrConnector._parse_legal_form("Omega Stavby SZČO") == "SZČO"
    assert OrsrConnector._parse_legal_form("Acme Slovakia s. r. o.") == "s. r. o."
    assert OrsrConnector._parse_legal_form(None) == ""


def test_live_results_are_cached():
    """Repeated lookups for the same IČO must not re-hit the network."""
    conn = OrsrConnector(mock=False)
    calls = []

    def fake_fetch(ico: str):
        calls.append(ico)
        from app.services.enrichment.orsr import CompanyProfile

        return CompanyProfile(name="Acme s. r. o.", ico=ico, status="Načítané z ORSR")

    conn._fetch = fake_fetch  # type: ignore[method-assign]
    conn.get_by_ico("11111111")
    conn.get_by_ico("11111111")
    assert len(calls) == 1
