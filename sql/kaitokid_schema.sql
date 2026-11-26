-- KaitoKid bot — PostgreSQL schema (Supabase, Postgres 17)
-- Replaces the MongoDB database (collections -> tables, all prefixed kk_).
-- Run with: supabase_mgmt.py query urgdnmbvdbmiqyyadumu "$(cat kaitokid_schema.sql)"
-- or via psql/asyncpg. Idempotent (CREATE TABLE IF NOT EXISTS).

-- afk: Mongo "users" {user_id, reason: {type, time, data, reason}}
CREATE TABLE IF NOT EXISTS kk_afk_users (
    user_id BIGINT PRIMARY KEY,
    reason JSONB NOT NULL DEFAULT '{}'::jsonb
);

-- afk: Mongo "cleanmode" {chat_id} (row present = cleanmode OFF; absent = ON)
CREATE TABLE IF NOT EXISTS kk_cleanmode (
    chat_id BIGINT PRIMARY KEY
);

-- blacklist: Mongo "blacklistFilters" {chat_id, filters: [word, ...]}
CREATE TABLE IF NOT EXISTS kk_blacklist_filters (
    chat_id BIGINT PRIMARY KEY,
    filters JSONB NOT NULL DEFAULT '[]'::jsonb
);

-- filters: Mongo "filters" {chat_id, filters: {name: filter}}
CREATE TABLE IF NOT EXISTS kk_filters (
    chat_id BIGINT PRIMARY KEY,
    filters JSONB NOT NULL DEFAULT '{}'::jsonb
);

-- funny: Mongo "funny" {chat_id, user_id, command, last_used}
CREATE TABLE IF NOT EXISTS kk_funny (
    chat_id BIGINT NOT NULL,
    user_id BIGINT NOT NULL,
    command TEXT NOT NULL,
    last_used TIMESTAMPTZ,
    PRIMARY KEY (chat_id, user_id, command)
);

-- gban: Mongo "gban" {user_id}
CREATE TABLE IF NOT EXISTS kk_gban (
    user_id BIGINT PRIMARY KEY
);

-- greetings: Mongo "greetings" {chat_id, welcome_enabled, custom_welcome_message, welcome_buttons, ban_on_leave_enabled}
CREATE TABLE IF NOT EXISTS kk_greetings (
    chat_id BIGINT PRIMARY KEY,
    welcome_enabled BOOLEAN NOT NULL DEFAULT FALSE,
    custom_welcome_message TEXT,
    welcome_buttons JSONB NOT NULL DEFAULT '[]'::jsonb,
    ban_on_leave_enabled BOOLEAN NOT NULL DEFAULT FALSE
);

-- imdb: Mongo "imdb" {user_id, lang}
CREATE TABLE IF NOT EXISTS kk_imdb (
    user_id BIGINT PRIMARY KEY,
    lang TEXT
);

-- karma: Mongo "karma" {chat_id, karma: {name: {...}}} plus toggle docs {chat_id_toggle}
-- Toggle rows use is_toggle = true on the same chat_id; karma rows use false.
CREATE TABLE IF NOT EXISTS kk_karma (
    chat_id BIGINT NOT NULL,
    is_toggle BOOLEAN NOT NULL DEFAULT FALSE,
    karma JSONB NOT NULL DEFAULT '{}'::jsonb,
    PRIMARY KEY (chat_id, is_toggle)
);

-- locale: Mongo "locale" {chat_id, lang, chat_type}
CREATE TABLE IF NOT EXISTS kk_locale (
    chat_id BIGINT PRIMARY KEY,
    lang TEXT,
    chat_type TEXT
);

-- notes: Mongo "notes" {chat_id, notes: {name: note}}
CREATE TABLE IF NOT EXISTS kk_notes (
    chat_id BIGINT PRIMARY KEY,
    notes JSONB NOT NULL DEFAULT '{}'::jsonb
);

-- report_links: Mongo "report_links" {chat_id, report_link_enabled, excluded_links}
CREATE TABLE IF NOT EXISTS kk_report_links (
    chat_id BIGINT PRIMARY KEY,
    report_link_enabled BOOLEAN NOT NULL DEFAULT FALSE,
    excluded_links JSONB NOT NULL DEFAULT '[]'::jsonb
);

-- sangmata: Mongo "sangmata" user docs {user_id, username, first_name, last_name}
-- plus toggle docs {chat_id_toggle} (same collection, different shape).
CREATE TABLE IF NOT EXISTS kk_sangmata (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT UNIQUE,
    username TEXT,
    first_name TEXT,
    last_name TEXT,
    chat_id_toggle BIGINT UNIQUE
);

-- users_chats: Mongo "userlist" {id, name, ban_status: {is_banned, ban_reason}}
CREATE TABLE IF NOT EXISTS kk_userlist (
    id BIGINT PRIMARY KEY,
    name TEXT,
    ban_status JSONB NOT NULL DEFAULT '{"is_banned": false, "ban_reason": ""}'::jsonb
);

-- users_chats: ban docs stored inside Mongo "userlist" {_id: user_id, reason}
CREATE TABLE IF NOT EXISTS kk_user_bans (
    user_id BIGINT PRIMARY KEY,
    reason TEXT NOT NULL DEFAULT ''
);

-- users_chats: Mongo "groups" {id, title, chat_status: {is_disabled, reason}}
CREATE TABLE IF NOT EXISTS kk_groups (
    id BIGINT PRIMARY KEY,
    title TEXT,
    chat_status JSONB NOT NULL DEFAULT '{"is_disabled": false, "reason": ""}'::jsonb
);

-- users_chats: Mongo "member_history" {chat_id, user_id, first_joined, last_joined, last_left, join_count}
CREATE TABLE IF NOT EXISTS kk_member_history (
    chat_id BIGINT NOT NULL,
    user_id BIGINT NOT NULL,
    first_joined TIMESTAMPTZ,
    last_joined TIMESTAMPTZ,
    last_left TIMESTAMPTZ,
    join_count INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (chat_id, user_id)
);

-- users_chats: Mongo "peers" (separate KaitoKidBot db) — Pyrogram peer docs.
-- Kept for API compatibility; empty unless something writes peers.
CREATE TABLE IF NOT EXISTS kk_peers (
    id BIGINT PRIMARY KEY,
    data JSONB NOT NULL DEFAULT '{}'::jsonb
);

-- warn: Mongo "warn" {chat_id, warns: {name: {...}}}
CREATE TABLE IF NOT EXISTS kk_warns (
    chat_id BIGINT PRIMARY KEY,
    warns JSONB NOT NULL DEFAULT '{}'::jsonb
);

-- autoapprove: Mongo "autoapprove" {chat_id}
CREATE TABLE IF NOT EXISTS kk_autoapprove (
    chat_id BIGINT PRIMARY KEY
);
