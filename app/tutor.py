"""Professor de IA (Claude) para corrigir o diário."""

import os

import anthropic
from pydantic import BaseModel, Field

DEFAULT_MODEL = "claude-haiku-5-5"

DEFAULT_LEARNER = """\
Brasileiro de nível iniciante, desenvolvedor de software. Quer conversar com naturalidade
e entender streamers americanos (Kai Cenat, IShowSpeed etc.), então inglês informal e
americano é bem-vindo."""

SYSTEM_PROMPT_TEMPLATE = """\
Você é um professor de inglês paciente e direto. Sobre o aluno:
{learner}

Ao corrigir um texto:
- "corrected": o texto com apenas os erros corrigidos, mantendo o estilo do aluno.
- "natural": como um americano diria isso de forma natural e informal.
- "mistakes": um item por erro real (gramática, vocabulário, ortografia, ordem das palavras).
  "original" é o trecho exato que o aluno escreveu, "correction" é a frase curta corrigida
  (vai virar um flashcard, então deve fazer sentido sozinha), "explanation" explica em
  português, em uma ou duas frases, o porquê.
  Não invente erros nem liste trechos que já estavam certos: se "correction" for igual a
  "original", não é um erro. Se estiver tudo certo, devolva a lista vazia.
- "encouragement": uma frase curta de incentivo em português, citando algo que o aluno acertou.
"""


class Mistake(BaseModel):
    original: str = Field(description="Trecho exato que o aluno escreveu")
    correction: str = Field(description="Versão corrigida, curta e autossuficiente")
    explanation: str = Field(description="Explicação curta em português")


class Correction(BaseModel):
    corrected: str
    natural: str
    mistakes: list[Mistake]
    encouragement: str


class TutorError(Exception):
    """Erro com mensagem amigável para mostrar na tela."""

    def __init__(self, message: str, status: int = 502):
        super().__init__(message)
        self.status = status


def model() -> str:
    return os.environ.get("ENGLISH_ZE_MODEL", DEFAULT_MODEL)


def system_prompt() -> str:
    learner = os.environ.get("ENGLISH_ZE_LEARNER", "").strip() or DEFAULT_LEARNER
    return SYSTEM_PROMPT_TEMPLATE.format(learner=learner)


def is_configured() -> bool:
    return bool(os.environ.get("ANTHROPIC_API_KEY"))


_client: anthropic.Anthropic | None = None


def _get_client() -> anthropic.Anthropic:
    global _client
    if _client is None:
        _client = anthropic.Anthropic()
    return _client


def correct_journal(text: str) -> Correction:
    if not is_configured():
        raise TutorError("Configure a ANTHROPIC_API_KEY no arquivo .env pra usar a IA.", 503)

    try:
        response = _get_client().messages.parse(
            model=model(),
            max_tokens=4000,
            system=system_prompt(),
            output_config={"effort": "low"},
            output_format=Correction,
            messages=[{"role": "user", "content": f"Corrija meu texto:\n\n{text}"}],
        )
    except anthropic.AuthenticationError:
        raise TutorError("A chave da API foi recusada. Confira a ANTHROPIC_API_KEY.", 503) from None
    except anthropic.RateLimitError:
        raise TutorError("Muitas requisições ou créditos esgotados. Tente de novo em instantes.", 429) from None
    except anthropic.APIStatusError as e:
        raise TutorError(f"Erro da API ({e.status_code}): {e.message}") from None
    except anthropic.APIConnectionError:
        raise TutorError("Sem conexão com a API. Confira sua internet.") from None

    if response.stop_reason == "refusal":
        raise TutorError("A IA não quis corrigir esse texto. Tente reescrever.", 422)
    if response.stop_reason == "max_tokens" or response.parsed_output is None:
        raise TutorError("A resposta veio incompleta. Tente um texto mais curto.")

    correction = response.parsed_output
    # Às vezes o modelo lista como "erro" um trecho que já estava certo; isso viraria card inútil.
    correction.mistakes = [m for m in correction.mistakes if _normalize(m.original) != _normalize(m.correction)]
    return correction


def _normalize(text: str) -> str:
    return " ".join(text.lower().strip(" .,!?").split())
