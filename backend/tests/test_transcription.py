def test_insights(client, auth_headers):
    r = client.post(
        "/api/transcription/insights",
        json={"transcript": "Zákazník má záujem o produkt a čaká na cenovú ponuku."},
        headers=auth_headers,
    )
    assert r.status_code == 200
    assert "summary" in r.json()


def test_transcribe_file_sandbox(client, auth_headers):
    r = client.post(
        "/api/transcription/transcribe",
        files={"file": ("call.wav", b"RIFFdummyaudiobytes", "audio/wav")},
        headers=auth_headers,
    )
    assert r.status_code == 200
    assert "text" in r.json()


def test_insights_empty_rejected(client, auth_headers):
    r = client.post("/api/transcription/insights", json={"transcript": "  "}, headers=auth_headers)
    assert r.status_code == 400
