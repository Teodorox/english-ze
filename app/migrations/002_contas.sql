-- Contas de usuário: cada pessoa tem os próprios cards, revisões (via cards) e diário.
-- Os dados que já existiam ficam sem dono (user_id NULL) até serem entregues a uma conta
-- com "python contas.py assumir-dados"; sem dono, eles não aparecem pra ninguém.

CREATE TABLE users (
    id            integer GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    email         text NOT NULL,
    name          text NOT NULL,
    password_hash text NOT NULL,
    timezone      text NOT NULL DEFAULT 'America/Sao_Paulo',
    learner       text NOT NULL DEFAULT '',  -- como a IA deve tratar essa pessoa na correção
    created_at    timestamptz NOT NULL DEFAULT now()
);
CREATE UNIQUE INDEX users_email_key ON users (lower(email));

-- Um aparelho conectado = uma linha. Guarda só o hash do token: quem ler o banco não consegue entrar.
CREATE TABLE sessions (
    token_hash bytea PRIMARY KEY,
    user_id    integer NOT NULL REFERENCES users (id) ON DELETE CASCADE,
    created_at timestamptz NOT NULL DEFAULT now(),
    expires_at timestamptz NOT NULL
);
CREATE INDEX sessions_user_idx ON sessions (user_id);

-- Convites de uso único (criados com "python contas.py convite").
CREATE TABLE invites (
    code       text PRIMARY KEY,
    note       text NOT NULL DEFAULT '',  -- pra quem é o convite
    created_at timestamptz NOT NULL DEFAULT now(),
    used_by    integer REFERENCES users (id) ON DELETE SET NULL,
    used_at    timestamptz
);

ALTER TABLE cards ADD COLUMN user_id integer REFERENCES users (id) ON DELETE CASCADE;
ALTER TABLE cards DROP CONSTRAINT cards_front_key;
ALTER TABLE cards ADD CONSTRAINT cards_user_front_key UNIQUE (user_id, front);
DROP INDEX cards_due_idx;
CREATE INDEX cards_user_due_idx ON cards (user_id, due);

ALTER TABLE journal ADD COLUMN user_id integer REFERENCES users (id) ON DELETE CASCADE;
CREATE INDEX journal_user_idx ON journal (user_id, id);
