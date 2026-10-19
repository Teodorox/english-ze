import io
import math
import struct
import wave

import pytest
from fastapi.testclient import TestClient

from app import transcribe


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("ENGLISH_DB", str(tmp_path / "test.db"))
    from app.main import app

    with TestClient(app) as c:
        yield c


def fake_model(text):
    """Modelo falso: os testes não baixam nem rodam o Whisper de verdade."""
    segment = type("Segment", (), {"text": f" {text} "})

    class Model:
        def transcribe(self, audio, **kwargs):
            assert kwargs["language"] == "en"
            assert "initial_prompt" not in kwargs  # sem dica da frase alvo: não "ajuda" a nota
            return [segment], None

    return Model()


def test_transcribe_endpoint(client, monkeypatch):
    monkeypatch.setattr(transcribe, "available", lambda: True)
    monkeypatch.setattr(transcribe, "_decode", lambda audio: audio)
    monkeypatch.setattr(transcribe, "_get_model", lambda: fake_model("What do you do for a living?"))
    res = client.post("/api/transcribe", content=b"fake-audio", headers={"Content-Type": "audio/webm"})
    assert res.status_code == 200
    assert res.json() == {"text": "What do you do for a living?"}


def test_empty_and_too_large_audio(client, monkeypatch):
    monkeypatch.setattr(transcribe, "available", lambda: True)
    assert client.post("/api/transcribe", content=b"").status_code == 400
    big = b"x" * (transcribe.MAX_AUDIO_BYTES + 1)
    assert client.post("/api/transcribe", content=big).status_code == 413


def test_broken_audio_gives_friendly_error(client, monkeypatch):
    monkeypatch.setattr(transcribe, "available", lambda: True)

    def broken(audio):
        raise ValueError("arquivo corrompido")

    monkeypatch.setattr(transcribe, "_decode", broken)
    res = client.post("/api/transcribe", content=b"lixo")
    assert res.status_code == 400
    assert "Grave de novo" in res.json()["detail"]


def test_not_installed(client, monkeypatch):
    monkeypatch.setattr(transcribe, "available", lambda: False)
    assert client.get("/api/transcribe/status").json()["available"] is False
    assert client.post("/api/transcribe", content=b"audio").status_code == 503


def test_decode_converts_to_16khz_mono():
    pytest.importorskip("av")
    buffer = io.BytesIO()
    with wave.open(buffer, "wb") as wav:  # 1 s de tom de 440 Hz, estéreo, 44.1 kHz
        wav.setnchannels(2)
        wav.setsampwidth(2)
        wav.setframerate(44100)
        samples = (int(8000 * math.sin(2 * math.pi * 440 * i / 44100)) for i in range(44100))
        wav.writeframes(b"".join(struct.pack("<hh", s, s) for s in samples))
    audio = transcribe._decode(buffer.getvalue())
    assert abs(len(audio) - 16000) < 400  # ~1 s em 16 kHz
    assert audio.dtype.name == "float32"
    assert 0.1 < float(abs(audio).max()) <= 1.0
