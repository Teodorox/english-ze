-- Trilhas de estudo: cada frase escrita à mão sabe de que objetivo, nível e situação ela é,
-- e em que ordem entra (track_step). As frases vêm de data/tracks e entram na conta no
-- primeiro acesso (ou quando os objetivos mudam). Cards da pessoa (minerados, do diário)
-- ficam com tudo vazio.

ALTER TABLE cards
    ADD COLUMN track text
        CHECK (track IN ('base', 'streamers', 'conversar', 'trabalho', 'musica', 'viagem', 'series', 'provas')),
    ADD COLUMN track_level text
        CHECK (track_level IN ('iniciante', 'basico', 'intermediario')),
    ADD COLUMN track_situation text CHECK (length(track_situation) <= 80),
    ADD COLUMN track_step smallint CHECK (track_step >= 0);
