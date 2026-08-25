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
