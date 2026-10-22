import logging
from contextlib import asynccontextmanager
from datetime import timedelta
from typing import Annotated, Literal

from fastapi import Depends, FastAPI, HTTPException, Path, Query, Request, Response
from fastapi.concurrency import run_in_threadpool
from psycopg.types.json import Jsonb
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from . import auth, db, quiz, security, srs, tracks, transcribe, tutor, web
from .config import load_env_file
from .progress import compute_streak

MISTAKES_CATEGORY = "meus-erros"
MAX_ID = 2**31 - 1  # maior id que cabe no banco: acima disso é 404 direto, sem erro 500
MAX_SPEECH_CHECKS_PER_DAY = 500  # bem acima de qualquer estudo de verdade; impede encher o banco
# Plano do dia pelo tempo escolhido: frases novas (~30 s cada) e um teto de revisões (~10 s cada).
NEW_PER_DAY = {5: 3, 10: 5, 15: 8, 20: 10, 30: 15}
REVIEWS_PER_MINUTE = 4

load_env_file()
log = logging.getLogger("english_ze.security")
login_limiter = auth.LoginLimiter()

# Toda rota de dados recebe quem está logado; sem login, responde 401 antes de rodar.
CurrentUser = Annotated[auth.User, Depends(auth.current_user)]
CardId = Annotated[int, Path(ge=1, le=MAX_ID)]
EntryId = Annotated[int, Path(ge=1, le=MAX_ID)]


@asynccontextmanager
async def lifespan(_: FastAPI):
    db.init_db()
    with db.connect() as conn:
        tracks.sync_everyone(conn)
    yield
    db.close_pool()


# Sem /docs nem /openapi.json: não publica o mapa da API pra quem não é do app.
app = FastAPI(title="English Zé", lifespan=lifespan, docs_url=None, redoc_url=None, openapi_url=None)
app.middleware("http")(security.protect)
app.add_middleware(
    security.BodyLimitMiddleware,
    per_path={"/api/transcribe": transcribe.MAX_AUDIO_BYTES + 1024},  # o áudio tem o limite dele
)


def _stripped(value: str) -> str:
    return value.strip()


class CardIn(BaseModel):
    front: str = Field(min_length=1, max_length=500)
    back: str = Field(min_length=1, max_length=500)
    note: str = Field(default="", max_length=1000)
    category: str = Field(default="geral", max_length=40)
    source: str = Field(default="", max_length=200)

    _strip = field_validator("front", "back", "note", "category", "source")(_stripped)


StudyMode = Literal["read", "listen"]


class ReviewIn(BaseModel):
    grade: int = Field(ge=0, le=3)
    mode: StudyMode | None = None  # sem modo = app antigo; a revisão vale do mesmo jeito


class SpeechCheckIn(BaseModel):
    """Resultado de um "Checar pronúncia": só os números, nunca o áudio nem o texto entendido."""

    model_config = ConfigDict(strict=True)  # "3" (texto) não vira 3

    words_total: int = Field(ge=1, le=500)
    words_ok: int = Field(ge=0, le=500)
    card_id: int | None = Field(default=None, ge=1, le=MAX_ID)

    @model_validator(mode="after")
    def _ok_within_total(self):
        if self.words_ok > self.words_total:
            raise ValueError("words_ok não pode passar de words_total")
        return self


class JournalIn(BaseModel):
    text: str = Field(min_length=1, max_length=5000)


class LoginIn(BaseModel):
    email: str = Field(max_length=254)
    password: str = Field(max_length=200)


class SignupIn(BaseModel):
    name: str = Field(min_length=1, max_length=60)
    email: str = Field(max_length=254)
    password: str = Field(min_length=auth.PASSWORD_MIN, max_length=200)
    invite: str = Field(max_length=40)
    timezone: str = Field(default=db.DEFAULT_TIMEZONE, max_length=64)  # o navegador manda o fuso do aparelho

    _strip = field_validator("name", "email", "invite")(_stripped)


# Perfil de estudo (primeiro acesso). As mesmas listas estão no banco (migrações 004 e 005).
Goal = Literal["streamers", "conversar", "trabalho", "musica", "viagem", "series", "provas"]
Level = Literal["iniciante", "basico", "intermediario"]
DailyMinutes = Literal[5, 10, 15, 20, 30]
Goals = Annotated[list[Goal], Field(min_length=1, max_length=7)]


def _unique(goals: list[str] | None) -> list[str] | None:
    return None if goals is None else list(dict.fromkeys(goals))  # tira repetidos, mantém a ordem


class ProfileIn(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=60)
    timezone: str | None = Field(default=None, max_length=64)
    learner: str | None = Field(default=None, max_length=1000)
    goals: Goals | None = None
    level: Level | None = None
    daily_minutes: DailyMinutes | None = None

    _goals = field_validator("goals")(_unique)


class OnboardingIn(BaseModel):
    goals: Goals
    level: Level
    daily_minutes: DailyMinutes

    _goals = field_validator("goals")(_unique)


class PasswordIn(BaseModel):
    current: str = Field(max_length=200)
    new: str = Field(min_length=auth.PASSWORD_MIN, max_length=200)


class ConfirmIn(BaseModel):
    password: str = Field(max_length=200)


# ---------- Conta ----------

def _client_ip(request: Request) -> str:
    return request.client.host if request.client else "desconhecido"


def _start_session(request: Request, response: Response, user_id: int) -> None:
    with db.connect() as conn:
        token = auth.create_session(conn, user_id)
    response.set_cookie(
        auth.COOKIE_NAME,
        token,
        max_age=auth.SESSION_SECONDS,
        httponly=True,
        samesite="lax",
        secure=request.url.scheme == "https",
    )


# Campos do perfil que a pessoa pode mudar, cada um com a sua consulta fixa.
PROFILE_UPDATES = {
    "name": "UPDATE users SET name = %s WHERE id = %s",
    "timezone": "UPDATE users SET timezone = %s WHERE id = %s",
    "learner": "UPDATE users SET learner = %s WHERE id = %s",
    "goals": "UPDATE users SET goals = %s WHERE id = %s",
    "level": "UPDATE users SET level = %s WHERE id = %s",
    "daily_minutes": "UPDATE users SET daily_minutes = %s WHERE id = %s",
}


def escape_like(text: str) -> str:
    """Busca literal: % e _ digitados viram texto, não curingas do LIKE."""
    return text.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


def _me(user: auth.User) -> dict:
    return {
        "id": user.id,
        "email": user.email,
        "name": user.name,
        "timezone": user.timezone,
        "learner": user.learner,
        "goals": user.goals,
        "level": user.level,
        "daily_minutes": user.daily_minutes,
        "onboarded": user.onboarded,
    }


@app.post("/api/login")
def login(body: LoginIn, request: Request, response: Response):
    keys = (f"ip:{_client_ip(request)}", f"email:{auth.normalize_email(body.email)}")
    if any(login_limiter.blocked(k) for k in keys):
        raise HTTPException(429, "Muitas tentativas erradas. Espere alguns minutos.")
    user_id = auth.authenticate(body.email, body.password)
    if user_id is None:
        for key in keys:
            login_limiter.fail(key)
        log.warning("Login recusado (ip %s)", _client_ip(request))
        raise HTTPException(401, "E-mail ou senha incorretos")
    for key in keys:
        login_limiter.reset(key)
    _start_session(request, response, user_id)
    return {"ok": True}


@app.post("/api/signup", status_code=201)
def signup(body: SignupIn, request: Request):
    """Cria a conta, mas não entra nela: a pessoa faz o login em seguida com o e-mail e a senha."""
    ip_key = f"signup:{_client_ip(request)}"
    if login_limiter.blocked(ip_key):
        raise HTTPException(429, "Muitas tentativas erradas. Espere alguns minutos.")
    if not auth.valid_email(body.email):
        raise HTTPException(422, "Esse e-mail não parece válido")
    if reason := auth.weak_password_reason(body.password, email=body.email, name=body.name):
        raise HTTPException(422, reason)
    if not auth.valid_timezone(body.timezone):
        body.timezone = db.DEFAULT_TIMEZONE

    with db.connect() as conn:
        # FOR UPDATE: o mesmo convite usado em dois cadastros ao mesmo tempo só vale pra um.
        invite = conn.execute(
            "SELECT code FROM invites WHERE code = %s AND used_by IS NULL FOR UPDATE",
            (auth.normalize_invite(body.invite),),
        ).fetchone()
        if invite is None:
            login_limiter.fail(ip_key)  # dificulta adivinhar códigos
            log.warning("Cadastro com convite inválido (ip %s)", _client_ip(request))
            raise HTTPException(403, "Código de convite inválido ou já usado")
        user_id = auth.create_user(
            conn, email=body.email, name=body.name, password=body.password, timezone=body.timezone
        )
        if user_id is None:
            login_limiter.fail(ip_key)  # dificulta descobrir quais e-mails têm conta
            raise HTTPException(409, "Já existe uma conta com esse e-mail. Entre com ela.")
        conn.execute("UPDATE invites SET used_by = %s, used_at = now() WHERE code = %s", (user_id, invite["code"]))
    return {"ok": True}


@app.post("/api/logout")
def logout(request: Request, response: Response):
    auth.end_session(auth.session_token(request))
    response.delete_cookie(auth.COOKIE_NAME)
    return {"ok": True}


@app.get("/api/me")
def me(user: CurrentUser):
    return _me(user)


@app.patch("/api/me")
def update_me(body: ProfileIn, user: CurrentUser):
    changes = body.model_dump(exclude_none=True)
    if "name" in changes:
        changes["name"] = changes["name"].strip()
        if not changes["name"]:
            raise HTTPException(422, "O nome não pode ficar vazio")
    if "timezone" in changes and not auth.valid_timezone(changes["timezone"]):
        raise HTTPException(422, "Fuso horário desconhecido")
    if "learner" in changes:
        changes["learner"] = changes["learner"].strip()
    with db.connect() as conn:
        # Uma consulta fixa por campo: nada do que chega na requisição vira parte do SQL.
        for column, query in PROFILE_UPDATES.items():
            if column in changes:
                conn.execute(query, (changes[column], user.id))
        updated = auth.load_user(conn, user.id)
        if "goals" in changes or "level" in changes:
            tracks.sync_user(conn, user.id, updated.goals, updated.level)
        return _me(updated)


@app.post("/api/me/onboarding")
def complete_onboarding(body: OnboardingIn, user: CurrentUser):
    """Respostas do primeiro acesso. Pode repetir: só a primeira data de conclusão fica."""
    with db.connect() as conn:
        conn.execute(
            "UPDATE users SET goals = %s, level = %s, daily_minutes = %s,"
            " onboarded_at = COALESCE(onboarded_at, now()) WHERE id = %s",
            (body.goals, body.level, body.daily_minutes, user.id),
        )
        tracks.sync_user(conn, user.id, body.goals, body.level)
        return _me(auth.load_user(conn, user.id))


@app.post("/api/me/password")
def change_password(body: PasswordIn, request: Request, user: CurrentUser):
    key = f"password:{user.id}"
    if login_limiter.blocked(key):
        raise HTTPException(429, "Muitas tentativas erradas. Espere alguns minutos.")
    if auth.authenticate(user.email, body.current) is None:
        login_limiter.fail(key)
        raise HTTPException(403, "A senha atual não confere")
    if reason := auth.weak_password_reason(body.new, email=user.email, name=user.name):
        raise HTTPException(422, reason)
    with db.connect() as conn:
        auth.set_password(conn, user.id, body.new)
        # Quem soubesse a senha antiga perde o acesso: os outros aparelhos saem; este continua.
        auth.end_other_sessions(conn, user.id, keep_token=auth.session_token(request))
    return {"ok": True}


@app.post("/api/me/logout-others")
def logout_others(request: Request, user: CurrentUser):
    with db.connect() as conn:
        count = auth.end_other_sessions(conn, user.id, keep_token=auth.session_token(request))
    return {"ended": count}


@app.delete("/api/me")
def delete_me(body: ConfirmIn, response: Response, user: CurrentUser):
    """Apaga a conta e tudo dela de verdade (cards, revisões, diário, sessões). Não tem volta."""
    key = f"password:{user.id}"
    if login_limiter.blocked(key):
        raise HTTPException(429, "Muitas tentativas erradas. Espere alguns minutos.")
    if auth.authenticate(user.email, body.password) is None:
        login_limiter.fail(key)
        raise HTTPException(403, "Senha incorreta")
    with db.connect() as conn:
        conn.execute("DELETE FROM users WHERE id = %s", (user.id,))
    log.warning("Conta %s apagada a pedido da pessoa", user.id)
    response.delete_cookie(auth.COOKIE_NAME)
    return {"ok": True}


# ---------- Estudo ----------

@app.get("/api/session")
def session(user: CurrentUser, new_limit: int | None = Query(None, ge=0, le=100)):
    """Revisões vencidas e frases novas de hoje, no tamanho do tempo que a pessoa escolheu.

    Revisões acumuladas seguram as frases novas: com metade do teto, vêm metade; no teto, nenhuma.
    new_limit troca a conta pelo número pedido (sem segurar).
    """
    today = user.today()
    reviews_cap = user.daily_minutes * REVIEWS_PER_MINUTE
    with db.connect() as conn:
        due_total = conn.execute(
            "SELECT COUNT(*) AS n FROM cards WHERE user_id = %s AND introduced_on IS NOT NULL AND due <= %s",
            (user.id, today),
        ).fetchone()["n"]
        due = conn.execute(
            "SELECT * FROM cards WHERE user_id = %s AND introduced_on IS NOT NULL AND due <= %s"
            " ORDER BY due, id LIMIT %s",
            (user.id, today, reviews_cap),
        ).fetchall()
        if new_limit is not None:
            new_per_day = new_limit
        elif due_total >= reviews_cap:
            new_per_day = 0
        elif due_total >= reviews_cap // 2:
            new_per_day = (NEW_PER_DAY[user.daily_minutes] + 1) // 2
        else:
            new_per_day = NEW_PER_DAY[user.daily_minutes]
        introduced_today = conn.execute(
            "SELECT COUNT(*) AS n FROM cards WHERE user_id = %s AND introduced_on = %s", (user.id, today)
        ).fetchone()["n"]
        remaining = max(0, new_per_day - introduced_today)
        # Prioridade dos novos: seus erros do diário, depois o que você minerou, depois as trilhas dos
        # seus objetivos no seu nível (track_step intercala as trilhas), depois o resto do deck.
        levels = list(tracks.LEVELS_FOR.get(user.level or "", ()))
        new = conn.execute(
            "SELECT * FROM cards WHERE user_id = %s AND introduced_on IS NULL"
            " ORDER BY CASE WHEN category = %s THEN 0 WHEN source != %s THEN 1"
            " WHEN track = ANY(%s) AND track_level = ANY(%s) THEN 2 ELSE 3 END, track_step NULLS LAST, id"
            " LIMIT %s",
            (user.id, MISTAKES_CATEGORY, db.SEED_SOURCE, tracks.tracks_for(user.goals), levels, remaining),
        ).fetchall()
        # Opções do estudo ativo: traduções erradas tiradas dos outros cards da própria pessoa.
        pool = conn.execute("SELECT id, back, category FROM cards WHERE user_id = %s", (user.id,)).fetchall()
    quiz.add_choices(due + new, pool)
    for card in due + new:
        del card["traps"]  # já viraram opções: o app não precisa saber quais são as pegadinhas
    return {
        "due": due,
        "new": new,
        "due_total": due_total,
        "new_per_day": new_per_day,
        "held_back": new_limit is None and new_per_day < NEW_PER_DAY[user.daily_minutes],
    }


@app.post("/api/cards/{card_id}/review")
def review(card_id: CardId, body: ReviewIn, user: CurrentUser):
    today = user.today()
    with db.connect() as conn:
        # FOR UPDATE: duas avaliações do mesmo card ao mesmo tempo (dois aparelhos) não se atropelam.
        row = conn.execute(
            "SELECT * FROM cards WHERE id = %s AND user_id = %s FOR UPDATE", (card_id, user.id)
        ).fetchone()
        if row is None:
            raise HTTPException(404, "Card não encontrado")
        state = srs.CardState(row["ease"], row["interval_days"], row["reps"], row["lapses"])
        new_state, due = srs.schedule(state, body.grade, today)
        conn.execute(
            "UPDATE cards SET ease = %s, interval_days = %s, reps = %s, lapses = %s, due = %s,"
            " introduced_on = COALESCE(introduced_on, %s) WHERE id = %s",
            (new_state.ease, new_state.interval_days, new_state.reps, new_state.lapses, due, today, card_id),
        )
        conn.execute(
            "INSERT INTO reviews (card_id, grade, mode, reviewed_on) VALUES (%s, %s, %s, %s)",
            (card_id, body.grade, body.mode, today),
        )
    return {"due": due.isoformat(), "interval_days": new_state.interval_days}


@app.post("/api/speech-checks", status_code=201)
def save_speech_check(body: SpeechCheckIn, user: CurrentUser):
    today = user.today()
    with db.connect() as conn:
        # Trava a linha da pessoa: dois envios ao mesmo tempo não passam juntos do limite do dia.
        conn.execute("SELECT 1 FROM users WHERE id = %s FOR UPDATE", (user.id,))
        done = conn.execute(
            "SELECT COUNT(*) AS n FROM speech_checks WHERE user_id = %s AND checked_on = %s", (user.id, today)
        ).fetchone()["n"]
        if done >= MAX_SPEECH_CHECKS_PER_DAY:
            raise HTTPException(429, "Limite de checagens de hoje atingido. Volte amanhã!")
        if body.card_id is not None and conn.execute(
            "SELECT 1 FROM cards WHERE id = %s AND user_id = %s", (body.card_id, user.id)
        ).fetchone() is None:
            raise HTTPException(404, "Card não encontrado")
        row = conn.execute(
            "INSERT INTO speech_checks (user_id, card_id, words_total, words_ok, checked_on)"
            " VALUES (%s, %s, %s, %s, %s) RETURNING id, score",
            (user.id, body.card_id, body.words_total, body.words_ok, today),
        ).fetchone()
    return {"id": row["id"], "score": row["score"]}


# ---------- Cards ----------

@app.get("/api/cards")
def list_cards(
    user: CurrentUser,
    q: Annotated[str, Query(max_length=100)] = "",
    category: Annotated[str, Query(max_length=40)] = "",
):
    sql = "SELECT * FROM cards WHERE user_id = %s"
    params: list = [user.id]
    if q:
        sql += " AND (front ILIKE %s OR back ILIKE %s OR note ILIKE %s)"
        params += [f"%{escape_like(q)}%"] * 3
    if category:
        sql += " AND category = %s"
        params.append(category)
    sql += " ORDER BY id DESC"
    with db.connect() as conn:
        return conn.execute(sql, params).fetchall()


@app.get("/api/categories")
def categories(user: CurrentUser):
    with db.connect() as conn:
        rows = conn.execute(
            "SELECT DISTINCT category FROM cards WHERE user_id = %s ORDER BY category", (user.id,)
        ).fetchall()
    return [r["category"] for r in rows]


@app.post("/api/cards", status_code=201)
def create_card(card: CardIn, user: CurrentUser):
    with db.connect() as conn:
        row = conn.execute(
            "INSERT INTO cards (user_id, front, back, note, category, source) VALUES (%s, %s, %s, %s, %s, %s)"
            " ON CONFLICT (user_id, front) DO NOTHING RETURNING *",
            (user.id, card.front, card.back, card.note, card.category or "geral", card.source),
        ).fetchone()
    if row is None:
        raise HTTPException(409, "Esse card já existe")
    return row


@app.delete("/api/cards/{card_id}", status_code=204)
def delete_card(card_id: CardId, user: CurrentUser):
    with db.connect() as conn:
        cur = conn.execute("DELETE FROM cards WHERE id = %s AND user_id = %s", (card_id, user.id))
    if cur.rowcount == 0:
        raise HTTPException(404, "Card não encontrado")


# ---------- Diário ----------

@app.get("/api/journal")
def list_journal(user: CurrentUser):
    with db.connect() as conn:
        return conn.execute(
            "SELECT * FROM journal WHERE user_id = %s ORDER BY id DESC LIMIT 50", (user.id,)
        ).fetchall()


@app.post("/api/journal", status_code=201)
def create_journal(entry: JournalIn, user: CurrentUser):
    with db.connect() as conn:
        return conn.execute(
            "INSERT INTO journal (user_id, text) VALUES (%s, %s) RETURNING *", (user.id, entry.text.strip())
        ).fetchone()


@app.post("/api/journal/{entry_id}/correct")
def correct_journal(entry_id: EntryId, user: CurrentUser):
    with db.connect() as conn:
        row = conn.execute(
            "SELECT * FROM journal WHERE id = %s AND user_id = %s", (entry_id, user.id)
        ).fetchone()
    if row is None:
        raise HTTPException(404, "Entrada não encontrada")

    # A chamada à IA fica fora da conexão pra não segurar o banco enquanto espera.
    try:
        correction = tutor.correct_journal(row["text"], learner=user.learner)
    except tutor.TutorError as e:
        raise HTTPException(e.status, str(e)) from None

    cards_created = 0
    with db.connect() as conn:
        conn.execute(
            "UPDATE journal SET correction = %s WHERE id = %s AND user_id = %s",
            (Jsonb(correction.model_dump()), entry_id, user.id),
        )
        for mistake in correction.mistakes:
            cur = conn.execute(
                "INSERT INTO cards (user_id, front, back, note, category, source) VALUES (%s, %s, %s, %s, %s, %s)"
                " ON CONFLICT (user_id, front) DO NOTHING",
                (user.id, mistake.correction, mistake.explanation, f'Você escreveu: "{mistake.original}"',
                 MISTAKES_CATEGORY, "diário"),
            )
            cards_created += cur.rowcount
    return {"correction": correction.model_dump(), "cards_created": cards_created}


@app.get("/api/tutor/status")
def tutor_status(_: CurrentUser):
    return {"enabled": tutor.is_configured(), "model": tutor.model()}


# ---------- Progresso ----------

@app.get("/api/stats")
def stats(user: CurrentUser):
    today = user.today()
    with db.connect() as conn:
        days = {
            r["reviewed_on"]
            for r in conn.execute(
                "SELECT DISTINCT r.reviewed_on FROM reviews r JOIN cards c ON c.id = r.card_id WHERE c.user_id = %s",
                (user.id,),
            )
        }
        per_day = {
            r["reviewed_on"]: r["n"]
            for r in conn.execute(
                "SELECT r.reviewed_on, COUNT(*) AS n FROM reviews r JOIN cards c ON c.id = r.card_id"
                " WHERE c.user_id = %s AND r.reviewed_on >= %s GROUP BY r.reviewed_on",
                (user.id, today - timedelta(days=13)),
            )
        }
        totals = conn.execute(
            "SELECT COUNT(*) AS total_cards,"
            " COUNT(*) FILTER (WHERE introduced_on IS NOT NULL) AS learned,"
            " COUNT(*) FILTER (WHERE interval_days >= 21) AS mature,"
            " COUNT(*) FILTER (WHERE introduced_on IS NOT NULL AND due <= %s) AS due_today,"
            " COUNT(*) FILTER (WHERE introduced_on IS NOT NULL AND due = %s) AS due_tomorrow"
            " FROM cards WHERE user_id = %s",
            (today, today + timedelta(days=1), user.id),
        ).fetchone()
        speech_today = conn.execute(
            "SELECT COUNT(*) AS n FROM speech_checks WHERE user_id = %s AND checked_on = %s", (user.id, today)
        ).fetchone()["n"]

    history = []
    for i in range(13, -1, -1):
        day = today - timedelta(days=i)
        history.append({"day": day.isoformat(), "reviews": per_day.get(day, 0)})

    return {
        "streak": compute_streak(days, today),
        "reviews_today": per_day.get(today, 0),
        "speech_checks_today": speech_today,
        **totals,
        "history": history,
    }


# ---------- Transcrição (checar pronúncia) ----------

@app.get("/api/transcribe/status")
def transcribe_status(_: CurrentUser):
    return {"available": transcribe.available(), "model": transcribe.model_name()}


@app.post("/api/transcribe")
async def transcribe_audio(request: Request, _: CurrentUser):
    """Recebe a gravação (corpo cru, ex.: audio/webm ou audio/mp4) e devolve o texto entendido."""
    audio = await request.body()
    try:
        # O Whisper é pesado: roda numa thread pra não travar o servidor.
        text = await run_in_threadpool(transcribe.transcribe, audio)
    except transcribe.TranscribeError as e:
        raise HTTPException(e.status, str(e)) from None
    return {"text": text}


# ---------- App React (precisa ser a última rota) ----------

@app.get("/{path:path}", include_in_schema=False)
def frontend(path: str):
    return web.serve(path)
