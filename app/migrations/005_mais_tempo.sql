-- Tempo por dia: além de 5, 10 e 15 minutos, aceita 20 (focado) e 30 (intensivo).

ALTER TABLE users
    DROP CONSTRAINT users_daily_minutes_check,
    ADD CONSTRAINT users_daily_minutes_check CHECK (daily_minutes IN (5, 10, 15, 20, 30));
