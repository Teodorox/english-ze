from contextlib import asynccontextmanager
from datetime import timedelta

from fastapi import FastAPI, HTTPException, Query, Request, Response
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import JSONResponse
from psycopg.types.json import Jsonb
from pydantic import BaseModel, Field, field_validator

from . import auth, db, srs, transcribe, tutor, web
from .config import load_env_file
from .progress import compute_streak

MISTAKES_CATEGORY = "meus-erros"
PUBLIC_API_PATHS = {"/api/login"}

load_env_file()
login_limiter = auth.LoginLimiter()


@asynccontextmanager
async def lifespan(_: FastAPI):
    db.init_db()
    yield
    db.close_pool()


app = FastAPI(title="English Ze", lifespan=lifespan)


@app.middleware("http")
async def require_login(request: Request, call_next):
    """Protege os dados (a API). As telas do app são públicas: sem login, o React mostra o login."""
    path = request.url.path
    if not path.startswith("/api/") or path in PUBLIC_API_PATHS or not auth.enabled():
        return await call_next(request)
    if auth.valid_token(request.cookies.get(auth.COOKIE_NAME, "")):
        return await call_next(request)
    return JSONResponse({"detail": "Faça login"}, status_code=401)


class CardIn(BaseModel):
    front: str = Field(min_length=1, max_length=500)
    back: str = Field(min_length=1, max_length=500)
    note: str = Field(default="", max_length=1000)
    category: str = Field(default="geral", max_length=40)
    source: str = Field(default="", max_length=200)

    @field_validator("front", "back", "note", "category", "source")
    @classmethod
    def strip(cls, value: str) -> str:
        return value.strip()


class ReviewIn(BaseModel):
    grade: int = Field(ge=0, le=3)


class JournalIn(BaseModel):
    text: str = Field(min_length=1, max_length=5000)


class LoginIn(BaseModel):
    password: str = Field(max_length=200)


# ---------- Login ----------

@app.post("/api/login")
def login(body: LoginIn, request: Request, response: Response):
    if not auth.enabled():
        return {"ok": True}
    client = request.client.host if request.client else "desconhecido"
    if login_limiter.blocked(client):
        raise HTTPException(429, "Muitas tentativas erradas. Espere alguns minutos.")
    if not auth.check_password(body.password):
        login_limiter.fail(client)
        raise HTTPException(401, "Senha incorreta")
    login_limiter.reset(client)
    response.set_cookie(
        auth.COOKIE_NAME,
        auth.make_token(),
        max_age=auth.SESSION_SECONDS,
        httponly=True,
        samesite="lax",
        secure=request.url.scheme == "https",
    )
    return {"ok": True}


@app.post("/api/logout")
def logout(response: Response):
    response.delete_cookie(auth.COOKIE_NAME)
    return {"ok": True}


@app.get("/api/auth/status")
def auth_status():
    return {"enabled": auth.enabled()}


# ---------- Estudo ----------

@app.get("/api/session")
def session(new_limit: int = Query(10, ge=0, le=100)):
    today = db.today()
    with db.connect() as conn:
        due = conn.execute(
            "SELECT * FROM cards WHERE introduced_on IS NOT NULL AND due <= %s ORDER BY due, id",
            (today,),
        ).fetchall()
        introduced_today = conn.execute(
            "SELECT COUNT(*) AS n FROM cards WHERE introduced_on = %s", (today,)
        ).fetchone()["n"]
        remaining = max(0, new_limit - introduced_today)
        # Prioridade dos novos: seus erros do diário, depois o que você minerou, depois o deck inicial.
        new = conn.execute(
            "SELECT * FROM cards WHERE introduced_on IS NULL"
            " ORDER BY CASE WHEN category = %s THEN 0 WHEN source != %s THEN 1 ELSE 2 END, id"
            " LIMIT %s",
            (MISTAKES_CATEGORY, db.SEED_SOURCE, remaining),
        ).fetchall()
    return {"due": due, "new": new}


@app.post("/api/cards/{card_id}/review")
def review(card_id: int, body: ReviewIn):
    today = db.today()
    with db.connect() as conn:
        # FOR UPDATE: duas avaliações do mesmo card ao mesmo tempo (dois aparelhos) não se atropelam.
        row = conn.execute("SELECT * FROM cards WHERE id = %s FOR UPDATE", (card_id,)).fetchone()
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
            "INSERT INTO reviews (card_id, grade, reviewed_on) VALUES (%s, %s, %s)",
            (card_id, body.grade, today),
        )
    return {"due": due.isoformat(), "interval_days": new_state.interval_days}


# ---------- Cards ----------

@app.get("/api/cards")
def list_cards(q: str = "", category: str = ""):
    sql = "SELECT * FROM cards WHERE TRUE"
    params: list[str] = []
    if q:
        sql += " AND (front ILIKE %s OR back ILIKE %s OR note ILIKE %s)"
        params += [f"%{q}%"] * 3
    if category:
        sql += " AND category = %s"
        params.append(category)
    sql += " ORDER BY id DESC"
    with db.connect() as conn:
        return conn.execute(sql, params).fetchall()


@app.get("/api/categories")
def categories():
    with db.connect() as conn:
        rows = conn.execute("SELECT DISTINCT category FROM cards ORDER BY category").fetchall()
    return [r["category"] for r in rows]


@app.post("/api/cards", status_code=201)
def create_card(card: CardIn):
    with db.connect() as conn:
        row = conn.execute(
            "INSERT INTO cards (front, back, note, category, source) VALUES (%s, %s, %s, %s, %s)"
            " ON CONFLICT (front) DO NOTHING RETURNING *",
            (card.front, card.back, card.note, card.category or "geral", card.source),
        ).fetchone()
    if row is None:
        raise HTTPException(409, "Esse card já existe")
    return row


@app.delete("/api/cards/{card_id}", status_code=204)
def delete_card(card_id: int):
    with db.connect() as conn:
        cur = conn.execute("DELETE FROM cards WHERE id = %s", (card_id,))
    if cur.rowcount == 0:
        raise HTTPException(404, "Card não encontrado")


# ---------- Diário ----------

@app.get("/api/journal")
def list_journal():
    with db.connect() as conn:
        return conn.execute("SELECT * FROM journal ORDER BY id DESC LIMIT 50").fetchall()


@app.post("/api/journal", status_code=201)
def create_journal(entry: JournalIn):
    with db.connect() as conn:
        return conn.execute(
            "INSERT INTO journal (text) VALUES (%s) RETURNING *", (entry.text.strip(),)
        ).fetchone()


@app.post("/api/journal/{entry_id}/correct")
def correct_journal(entry_id: int):
    with db.connect() as conn:
        row = conn.execute("SELECT * FROM journal WHERE id = %s", (entry_id,)).fetchone()
    if row is None:
        raise HTTPException(404, "Entrada não encontrada")

    # A chamada à IA fica fora da conexão pra não segurar o banco enquanto espera.
    try:
        correction = tutor.correct_journal(row["text"])
    except tutor.TutorError as e:
        raise HTTPException(e.status, str(e)) from None

    cards_created = 0
    with db.connect() as conn:
        conn.execute(
            "UPDATE journal SET correction = %s WHERE id = %s", (Jsonb(correction.model_dump()), entry_id)
        )
        for mistake in correction.mistakes:
            cur = conn.execute(
                "INSERT INTO cards (front, back, note, category, source) VALUES (%s, %s, %s, %s, %s)"
                " ON CONFLICT (front) DO NOTHING",
                (mistake.correction, mistake.explanation, f'Você escreveu: "{mistake.original}"',
                 MISTAKES_CATEGORY, "diário"),
            )
            cards_created += cur.rowcount
    return {"correction": correction.model_dump(), "cards_created": cards_created}


@app.get("/api/tutor/status")
def tutor_status():
    return {"enabled": tutor.is_configured(), "model": tutor.model()}


# ---------- Progresso ----------

@app.get("/api/stats")
def stats():
    today = db.today()
    with db.connect() as conn:
        days = {r["reviewed_on"] for r in conn.execute("SELECT DISTINCT reviewed_on FROM reviews")}
        per_day = {
            r["reviewed_on"]: r["n"]
            for r in conn.execute(
                "SELECT reviewed_on, COUNT(*) AS n FROM reviews WHERE reviewed_on >= %s GROUP BY reviewed_on",
                (today - timedelta(days=13),),
            )
        }
        totals = conn.execute(
            "SELECT COUNT(*) AS total_cards,"
            " COUNT(*) FILTER (WHERE introduced_on IS NOT NULL) AS learned,"
            " COUNT(*) FILTER (WHERE interval_days >= 21) AS mature,"
            " COUNT(*) FILTER (WHERE introduced_on IS NOT NULL AND due <= %s) AS due_today,"
            " COUNT(*) FILTER (WHERE introduced_on IS NOT NULL AND due = %s) AS due_tomorrow"
            " FROM cards",
            (today, today + timedelta(days=1)),
        ).fetchone()

    history = []
    for i in range(13, -1, -1):
        day = today - timedelta(days=i)
        history.append({"day": day.isoformat(), "reviews": per_day.get(day, 0)})

    return {
        "streak": compute_streak(days, today),
        "reviews_today": per_day.get(today, 0),
        **totals,
        "history": history,
    }


# ---------- Transcrição (checar pronúncia) ----------

@app.get("/api/transcribe/status")
def transcribe_status():
    return {"available": transcribe.available(), "model": transcribe.model_name()}


@app.post("/api/transcribe")
async def transcribe_audio(request: Request):
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
