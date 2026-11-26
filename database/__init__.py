"""PostgreSQL (asyncpg) database layer for KaitoKid — replaces MongoDB/Motor.

Single shared asyncpg pool, created lazily on first use (asyncpg needs a
running event loop, so the pool cannot be built at import time). The DSN
comes from DATABASE_URL (config.env / environment), falling back to the
legacy DATABASE_URI variable. It points at the Supabase Postgres for this
bot (direct host; the Supabase pooler tenant is not synced for this project
yet, so the pooler URI is not used).

Compatibility: `dbname` is kept as a small dict-like shim so code doing
dbname["autoapprove"] keeps working (only autoapprove.py uses it). It
returns a PgCollection exposing the Motor subset that plugin needs
(count_documents / insert_one / delete_one). This is not a full Motor
emulation; the database/* modules use the pool helpers below directly.
"""
import json
import os

import asyncpg

_pool: asyncpg.Pool | None = None


async def _init_conn(conn: asyncpg.Connection) -> None:
    """Register dict/list <-> JSONB codecs on a new pool connection.

    asyncpg returns jsonb as plain text by default, so without this a
    dict parameter is rejected and a fetched JSONB value comes back as a
    string. With these codecs, dict/list values round-trip naturally.
    """
    await conn.set_type_codec(
        "jsonb",
        encoder=lambda v: json.dumps(v, ensure_ascii=False),
        decoder=lambda v: json.loads(v),
        schema="pg_catalog",
        format="text",
    )
    await conn.set_type_codec(
        "json",
        encoder=lambda v: json.dumps(v, ensure_ascii=False),
        decoder=lambda v: json.loads(v),
        schema="pg_catalog",
        format="text",
    )


def _dsn() -> str:
    dsn = os.environ.get("DATABASE_URL") or os.environ.get("DATABASE_URI", "")
    if not dsn:
        raise RuntimeError(
            "DATABASE_URL (or DATABASE_URI) is not set; cannot open the database pool"
        )
    return dsn


async def get_pool() -> asyncpg.Pool:
    """Return the shared asyncpg pool, creating it on first use."""
    global _pool
    if _pool is None or _pool.is_closing():
        _pool = await asyncpg.create_pool(
            _dsn(), min_size=1, max_size=10, timeout=30, init=_init_conn
        )
    return _pool


async def close_pool() -> None:
    """Close the shared pool (called on shutdown, if needed)."""
    global _pool
    if _pool is not None:
        await _pool.close()
        _pool = None


async def fetchrow(query, *args):
    pool = await get_pool()
    async with pool.acquire() as conn:
        return await conn.fetchrow(query, *args)


async def fetch(query, *args):
    pool = await get_pool()
    async with pool.acquire() as conn:
        return await conn.fetch(query, *args)


async def fetchval(query, *args):
    pool = await get_pool()
    async with pool.acquire() as conn:
        return await conn.fetchval(query, *args)


async def execute(query, *args):
    pool = await get_pool()
    async with pool.acquire() as conn:
        return await conn.execute(query, *args)


class AsyncIterList(list):
    """A list that also supports `async for` (Motor cursors did).

    get_all_* helpers return this so plugins doing
    `async for row in await db.get_all_users():` keep working.
    """

    async def __aiter__(self):
        for item in self:
            yield item


class PgCollection:
    """Minimal Motor-collection-compatible wrapper over one table.

    Only the methods autoapprove.py uses are implemented. All operations
    are parameterised ($1, $2, ...) so no user input reaches the SQL.
    """

    def __init__(self, table: str):
        self._table = table

    async def count_documents(self, filter: dict) -> int:
        if "chat_id" in filter:
            return await fetchval(
                f"SELECT COUNT(*) FROM {self._table} WHERE chat_id = $1",
                filter["chat_id"],
            )
        return await fetchval(f"SELECT COUNT(*) FROM {self._table}")

    async def insert_one(self, doc: dict):
        cols = ", ".join(doc.keys())
        placeholders = ", ".join(f"${i + 1}" for i in range(len(doc)))
        await execute(
            f"INSERT INTO {self._table} ({cols}) VALUES ({placeholders}) "
            "ON CONFLICT DO NOTHING",
            *doc.values(),
        )

    async def delete_one(self, filter: dict):
        if "chat_id" in filter:
            await execute(
                f"DELETE FROM {self._table} WHERE chat_id = $1", filter["chat_id"]
            )


class _DbName:
    """dict-like shim: dbname["autoapprove"] -> PgCollection."""

    _TABLES = {"autoapprove": "kk_autoapprove"}

    def __getitem__(self, name: str) -> PgCollection:
        return PgCollection(self._TABLES[name])


dbname = _DbName()
