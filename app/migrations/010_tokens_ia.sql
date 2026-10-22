-- Quantos tokens cada correção por IA gastou, pra saber o custo real (só os números, nunca o texto).
-- Ficam vazios quando a IA não respondeu (erro, sem conexão).
ALTER TABLE usage_events
    ADD COLUMN input_tokens  integer CHECK (input_tokens >= 0),
    ADD COLUMN output_tokens integer CHECK (output_tokens >= 0);
