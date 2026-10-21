-- Prática de fala guardada no servidor e modo de cada revisão (base pro plano do dia e pro nível por habilidade).

-- Modo em que o card foi estudado: 'read' (Ler) ou 'listen' (Ouvir). Revisões antigas ficam sem modo.
ALTER TABLE reviews
    ADD COLUMN mode text CHECK (mode IN ('read', 'listen'));

-- Cada "Checar pronúncia" da tela Falar. Guarda só os números: nem o áudio nem o texto entendido
-- saem do momento da checagem. card_id é preenchido quando a frase praticada é um card da pessoa.
CREATE TABLE speech_checks (
    id          integer GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    user_id     integer NOT NULL REFERENCES users (id) ON DELETE CASCADE,
    card_id     integer REFERENCES cards (id) ON DELETE SET NULL,
    words_total smallint NOT NULL CHECK (words_total BETWEEN 1 AND 500),
    words_ok    smallint NOT NULL CHECK (words_ok BETWEEN 0 AND words_total),
    -- A nota sai das palavras, no próprio banco: não tem como gravar uma nota que não bate com elas.
    -- (NULLIF: com total zero, a conta não quebra e o CHECK acima recusa a linha.)
    score       smallint GENERATED ALWAYS AS (round(100.0 * words_ok / NULLIF(words_total, 0))) STORED,
    checked_on  date NOT NULL,
    checked_at  timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX speech_checks_user_day_idx ON speech_checks (user_id, checked_on);
