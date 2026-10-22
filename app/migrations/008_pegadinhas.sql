-- Pegadinhas: traduções quase certas, escritas à mão pra cada frase das trilhas, que mudam
-- justamente a palavra-chave (negação, pessoa, tempo, o sentido da gíria). Aparecem como
-- opções erradas no estudo ativo. Cards da pessoa (minerados, do diário) ficam sem.

ALTER TABLE cards
    ADD COLUMN traps text[] NOT NULL DEFAULT '{}' CHECK (cardinality(traps) <= 3);
