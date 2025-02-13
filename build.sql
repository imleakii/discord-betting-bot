CREATE TABLE IF NOT EXISTS users (
    discord_id BIGINT PRIMARY KEY NOT NULL,
    coins INT unsigned NOT NULL DEFAULT 0
);

