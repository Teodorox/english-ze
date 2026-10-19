"""Transcrição de voz no servidor com o Whisper (faster-whisper), pra checar a pronúncia.

Funciona em qualquer navegador (inclusive no Safari do iPhone, que recusa o
reconhecimento de voz próprio). É opcional: sem o pacote instalado, o app usa o
reconhecimento do navegador.

O modelo (~150 MB) é baixado na primeira vez para data/models/.
"""

import io
import os
import threading

from .config import ROOT

DEFAULT_MODEL = "base.en"
MAX_AUDIO_BYTES = 5 * 1024 * 1024  # ~ alguns minutos de áudio comprimido; uma frase tem bem menos
MODELS_DIR = ROOT / "data" / "models"

_model = None
_lock = threading.Lock()


class TranscribeError(Exception):
    def __init__(self, message: str, status: int = 400):
        super().__init__(message)
        self.status = status


def available() -> bool:
    try:
        import faster_whisper  # noqa: F401
    except ImportError:
        return False
    return True


def model_name() -> str:
    return os.environ.get("ENGLISH_ZE_WHISPER_MODEL", DEFAULT_MODEL)


def _get_model():
    global _model
    if _model is None:
        from faster_whisper import WhisperModel

        # int8 no processador: rápido e leve, sem precisar de placa de vídeo.
        _model = WhisperModel(model_name(), device="cpu", compute_type="int8", download_root=str(MODELS_DIR))
    return _model


def _decode(audio: bytes):
    """Converte qualquer áudio (webm do Chrome, mp4 do Safari, wav...) em 16 kHz mono, como o Whisper espera.

    Feito aqui, e não pelo faster-whisper, porque o decodificador dele depende de um
    parâmetro que versões novas da biblioteca de áudio (av) removeram.
    """
    import av
    import numpy as np

    chunks = []
    with av.open(io.BytesIO(audio), mode="r") as container:
        resampler = av.AudioResampler(format="s16", layout="mono", rate=16000)
        for frame in container.decode(audio=0):
            chunks.extend(out.to_ndarray() for out in resampler.resample(frame))
        chunks.extend(out.to_ndarray() for out in resampler.resample(None))  # esvazia o que sobrou
    if not chunks:
        raise ValueError("áudio sem som")
    return np.concatenate(chunks, axis=1).flatten().astype(np.float32) / 32768.0


def transcribe(audio: bytes) -> str:
    if not available():
        raise TranscribeError("Transcrição no servidor não instalada.", 503)
    if not audio:
        raise TranscribeError("Áudio vazio. Grave de novo.")
    if len(audio) > MAX_AUDIO_BYTES:
        raise TranscribeError("Áudio muito longo. Grave só a frase.", 413)

    # Sem "prompt" com a frase alvo de propósito: ele faria o Whisper "ouvir" o que
    # esperamos e a nota de pronúncia ficaria boa demais.
    with _lock:
        try:
            segments, _ = _get_model().transcribe(_decode(audio), language="en", beam_size=5, vad_filter=True)
            text = " ".join(segment.text.strip() for segment in segments)
        except Exception as err:  # áudio corrompido ou formato não suportado
            raise TranscribeError(f"Não consegui entender o áudio ({type(err).__name__}). Grave de novo.") from None
    return text.strip()
