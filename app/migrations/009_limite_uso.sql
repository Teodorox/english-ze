-- Uso dos recursos caros (correção por IA, que gasta a chave da API, e transcrição de voz, que pesa
-- no processador), pra ter um teto por dia. Cada pedido é anotado antes de rodar: mesmo os que dão
-- erro contam, senão daria pra forçar erros e gastar sem limite.
CREATE TABLE usage_events (
    id       integer GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    user_id  integer NOT NULL REFERENCES users (id) ON DELETE CASCADE,
    kind     text NOT NULL CHECK (kind IN ('correction', 'transcribe')),
    used_on  date NOT NULL,
    used_at  timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX usage_events_user_day_idx ON usage_events (user_id, kind, used_on);
