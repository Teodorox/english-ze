import json
import sqlite3
from contextlib import asynccontextmanager
from datetime import date, timedelta
from pathlib import Path

from fastapi import FastAPI, HTTPException, Query, Request, Response
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field, field_validator

from . import auth, db, srs, tutor
from .config import load_env_file
from .progress import compute_streak

STATIC_DIR = Path(__file__).resolve().parent.parent / "static"
MISTAKES_CATEGORY = "meus-erros"
PUBLIC_PATHS = {"/login.html", "/style.css", "/api/login"}

load_env_file()
login_limiter = auth.LoginLimiter()


@asynccontextmanager
async def lifespan(_: FastAPI):
    db.init_db()
    yield


app = FastAPI(title="English Ze", lifespan=lifespan)


@app.middleware("http")
async def require_login(request: Request, call_next):
    path = request.url.path
    token = request.cookies.get(auth.COOKIE_NAME, "")
    if not auth.enabled() or path in PUBLIC_PATHS or auth.valid_token(token):
        return await call_next(request)
    if path.startswith("/api/"):
        return JSONResponse({"detail": "Faça login"}, status_code=401)
    return RedirectResponse("/login.html")


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


def _card(row: sqlite3.Row) -> dict:
    return dict(row)


# ---------- Estudo ----------

@app.get("/api/session")
def session(new_limit: int = Query(10, ge=0, le=100)):
    today = date.today().isoformat()
    with db.connect() as conn:
        due = conn.execute(
            "SELECT * FROM cards WHERE introduced_on IS NOT NULL AND due <= ? ORDER BY due, id",
            (today,),
        ).fetchall()
        introduced_today = conn.execute(
            "SELECT COUNT(*) FROM cards WHERE introduced_on = ?", (today,)
        ).fetchone()[0]
        remaining = max(0, new_limit - introduced_today)
        # Prioridade dos novos: seus erros do diário, depois o que você minerou, depois o deck inicial.
        new = conn.execute(
            "SELECT * FROM cards WHERE introduced_on IS NULL"
            " ORDER BY CASE WHEN category = ? THEN 0 WHEN source != ? THEN 1 ELSE 2 END, id"
            " LIMIT ?",
            (MISTAKES_CATEGORY, db.SEED_SOURCE, remaining),
        ).fetchall()
    return {"due": [_card(r) for r in due], "new": [_card(r) for r in new]}


@app.post("/api/cards/{card_id}/review")
def review(card_id: int, body: ReviewIn):
    today = date.today()
    with db.connect() as conn:
        row = conn.execute("SELECT * FROM cards WHERE id = ?", (card_id,)).fetchone()
        if row is None:
            raise HTTPException(404, "Card não encontrado")
        state = srs.CardState(row["ease"], row["interval_days"], row["reps"], row["lapses"])
        new_state, due = srs.schedule(state, body.grade, today)
        conn.execute(
            "UPDATE cards SET ease = ?, interval_days = ?, reps = ?, lapses = ?, due = ?,"
            " introduced_on = COALESCE(introduced_on, ?) WHERE id = ?",
            (new_state.ease, new_state.interval_days, new_state.reps, new_state.lapses,
             due.isoformat(), today.isoformat(), card_id),
        )
        conn.execute(
            "INSERT INTO reviews (card_id, grade, reviewed_on, reviewed_at) VALUES (?, ?, ?, ?)",
            (card_id, body.grade, today.isoformat(), db.now_iso()),
        )
    return {"due": due.isoformat(), "interval_days": new_state.interval_days}


# ---------- Cards ----------

@app.get("/api/cards")
def list_cards(q: str = "", category: str = ""):
    sql = "SELECT * FROM cards WHERE 1 = 1"
    params: list[str] = []
    if q:
        sql += " AND (front LIKE ? OR back LIKE ? OR note LIKE ?)"
        params += [f"%{q}%"] * 3
    if category:
        sql += " AND category = ?"
        params.append(category)
    sql += " ORDER BY id DESC"
    with db.connect() as conn:
        return [_card(r) for r in conn.execute(sql, params).fetchall()]


@app.get("/api/categories")
def categories():
    with db.connect() as conn:
        rows = conn.execute("SELECT DISTINCT category FROM cards ORDER BY category").fetchall()
    return [r["category"] for r in rows]


@app.post("/api/cards", status_code=201)
def create_card(card: CardIn):
    with db.connect() as conn:
        try:
            cur = conn.execute(
                "INSERT INTO cards (front, back, note, category, source, created_at)"
                " VALUES (?, ?, ?, ?, ?, ?)",
                (card.front, card.back, card.note, card.category or "geral", card.source, db.now_iso()),
            )
        except sqlite3.IntegrityError:
            raise HTTPException(409, "Esse card já existe") from None
        row = conn.execute("SELECT * FROM cards WHERE id = ?", (cur.lastrowid,)).fetchone()
    return _card(row)


@app.delete("/api/cards/{card_id}", status_code=204)
def delete_card(card_id: int):
    with db.connect() as conn:
        cur = conn.execute("DELETE FROM cards WHERE id = ?", (card_id,))
    if cur.rowcount == 0:
        raise HTTPException(404, "Card não encontrado")


# ---------- Diário ----------

def _journal(row: sqlite3.Row) -> dict:
    entry = dict(row)
    entry["correction"] = json.loads(entry["correction"]) if entry["correction"] else None
    return entry


@app.get("/api/journal")
def list_journal():
    with db.connect() as conn:
        rows = conn.execute("SELECT * FROM journal ORDER BY id DESC LIMIT 50").fetchall()
    return [_journal(r) for r in rows]


@app.post("/api/journal", status_code=201)
def create_journal(entry: JournalIn):
    with db.connect() as conn:
        cur = conn.execute(
            "INSERT INTO journal (text, created_at) VALUES (?, ?)", (entry.text.strip(), db.now_iso())
        )
        row = conn.execute("SELECT * FROM journal WHERE id = ?", (cur.lastrowid,)).fetchone()
    return _journal(row)


@app.post("/api/journal/{entry_id}/correct")
def correct_journal(entry_id: int):
    with db.connect() as conn:
        row = conn.execute("SELECT * FROM journal WHERE id = ?", (entry_id,)).fetchone()
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
            "UPDATE journal SET correction = ? WHERE id = ?", (correction.model_dump_json(), entry_id)
        )
        for mistake in correction.mistakes:
            cur = conn.execute(
                "INSERT OR IGNORE INTO cards (front, back, note, category, source, created_at)"
                " VALUES (?, ?, ?, ?, ?, ?)",
                (mistake.correction, mistake.explanation, f'Você escreveu: "{mistake.original}"',
                 MISTAKES_CATEGORY, "diário", db.now_iso()),
            )
            cards_created += cur.rowcount
    return {"correction": correction.model_dump(), "cards_created": cards_created}


@app.get("/api/tutor/status")
def tutor_status():
    return {"enabled": tutor.is_configured(), "model": tutor.model()}


# ---------- Progresso ----------

@app.get("/api/stats")
def stats():
    today = date.today()
    with db.connect() as conn:
        days = {
            date.fromisoformat(r[0])
            for r in conn.execute("SELECT DISTINCT reviewed_on FROM reviews").fetchall()
        }
        start = (today - timedelta(days=13)).isoformat()
        per_day = dict(
            conn.execute(
                "SELECT reviewed_on, COUNT(*) FROM reviews WHERE reviewed_on >= ? GROUP BY reviewed_on",
                (start,),
            ).fetchall()
        )
        totals = conn.execute(
            "SELECT COUNT(*) AS total,"
            " SUM(introduced_on IS NOT NULL) AS learned,"
            " SUM(interval_days >= 21) AS mature,"
            " SUM(introduced_on IS NOT NULL AND due <= ?) AS due_today,"
            " SUM(introduced_on IS NOT NULL AND due = ?) AS due_tomorrow"
            " FROM cards",
            (today.isoformat(), (today + timedelta(days=1)).isoformat()),
        ).fetchone()

    history = []
    for i in range(13, -1, -1):
        day = (today - timedelta(days=i)).isoformat()
        history.append({"day": day, "reviews": per_day.get(day, 0)})

    return {
        "streak": compute_streak(days, today),
        "reviews_today": per_day.get(today.isoformat(), 0),
        "total_cards": totals["total"] or 0,
        "learned": totals["learned"] or 0,
        "mature": totals["mature"] or 0,
        "due_today": totals["due_today"] or 0,
        "due_tomorrow": totals["due_tomorrow"] or 0,
        "history": history,
    }


app.mount("/", StaticFiles(directory=STATIC_DIR, html=True), name="static")
