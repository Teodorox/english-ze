"""Professor de IA (Claude) para corrigir o diário."""

import logging
import os

import anthropic
from pydantic import BaseModel, Field

DEFAULT_MODEL = "claude-haiku-5-5"
UNAVAILABLE = "A correção por IA não está disponível agora. Tente mais tarde."

log = logging.getLogger("english_ze.tutor")

# Usado quando a pessoa ainda não descreveu o próprio nível e objetivo (Ajustes > Conta).
DEFAULT_LEARNER = """\
Brasileiro aprendendo inglês. Quer conversar com naturalidade e entender o inglês americano
do dia a dia, então inglês informal é bem-vindo."""

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


def system_prompt(learner: str = "") -> str:
    return SYSTEM_PROMPT_TEMPLATE.format(learner=learner.strip() or DEFAULT_LEARNER)


def is_configured() -> bool:
    return bool(os.environ.get("ANTHROPIC_API_KEY"))


_client: anthropic.Anthropic | None = None


def _get_client() -> anthropic.Anthropic:
    global _client
    if _client is None:
        _client = anthropic.Anthropic()
    return _client


def correct_journal(text: str, learner: str = "") -> Correction:
    # Quem usa o app vê uma mensagem simples; o detalhe técnico fica só no registro do servidor.
    if not is_configured():
        log.error("ANTHROPIC_API_KEY não definida: a correção por IA está desligada")
        raise TutorError(UNAVAILABLE, 503)

    try:
        response = _get_client().messages.parse(
            model=model(),
            max_tokens=4000,
            system=system_prompt(learner),
            output_config={"effort": "low"},
            output_format=Correction,
            messages=[{"role": "user", "content": f"Corrija meu texto:\n\n{text}"}],
        )
    except anthropic.AuthenticationError:
        log.error("A API da Anthropic recusou a ANTHROPIC_API_KEY")
        raise TutorError(UNAVAILABLE, 503) from None
    except anthropic.RateLimitError:
        log.warning("API da Anthropic: limite de requisições ou créditos esgotados")
        raise TutorError("A IA está muito ocupada agora. Tente de novo em instantes.", 429) from None
    except anthropic.APIStatusError as e:
        log.error("API da Anthropic respondeu %s: %s", e.status_code, e.message)
        raise TutorError("A IA teve um problema ao corrigir. Tente de novo em instantes.") from None
    except anthropic.APIConnectionError:
        log.warning("Sem conexão com a API da Anthropic")
        raise TutorError("Não consegui falar com a IA agora. Tente de novo em instantes.") from None

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
