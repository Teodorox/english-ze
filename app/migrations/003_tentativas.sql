-- Tentativas erradas de login/cadastro, no banco (e não na memória do servidor): o limite continua
-- valendo depois de reiniciar e é o mesmo pra todos os servidores na nuvem. A chave é um hash
-- (do IP ou do e-mail), então a tabela não guarda dados pessoais legíveis.
CREATE TABLE auth_failures (
    key bytea NOT NULL,
    at  timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX auth_failures_key_idx ON auth_failures (key, at);
CREATE INDEX auth_failures_at_idx ON auth_failures (at);
