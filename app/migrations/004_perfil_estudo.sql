-- Perfil de estudo, respondido no primeiro acesso: objetivos, nível e tempo por dia.
-- Os valores aceitos ficam no próprio banco (CHECK), além da validação da API.
-- onboarded_at vazio = a pessoa ainda não passou pelo primeiro acesso (contas antigas também).

ALTER TABLE users
    ADD COLUMN goals text[] NOT NULL DEFAULT '{}'
        CHECK (goals <@ ARRAY['streamers', 'conversar', 'trabalho', 'musica', 'viagem', 'series', 'provas']::text[]),
    ADD COLUMN level text
        CHECK (level IN ('iniciante', 'basico', 'intermediario')),
    ADD COLUMN daily_minutes smallint NOT NULL DEFAULT 10
        CHECK (daily_minutes IN (5, 10, 15)),
    ADD COLUMN onboarded_at timestamptz;
