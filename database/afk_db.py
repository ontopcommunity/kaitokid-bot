from database import execute, fetch, fetchrow

cleanmode = {}


async def is_cleanmode_on(chat_id: int) -> bool:
    mode = cleanmode.get(chat_id)
    if not mode:
        row = await fetchrow("SELECT chat_id FROM kk_cleanmode WHERE chat_id = $1", chat_id)
        if not row:
            cleanmode[chat_id] = True
            return True
        cleanmode[chat_id] = False
        return False
    return mode


async def cleanmode_on(chat_id: int):
    cleanmode[chat_id] = True
    await execute("DELETE FROM kk_cleanmode WHERE chat_id = $1", chat_id)


async def cleanmode_off(chat_id: int):
    cleanmode[chat_id] = False
    await execute(
        "INSERT INTO kk_cleanmode (chat_id) VALUES ($1) ON CONFLICT DO NOTHING",
        chat_id,
    )


async def is_afk(user_id: int) -> bool:
    row = await fetchrow("SELECT reason FROM kk_afk_users WHERE user_id = $1", user_id)
    return (True, row["reason"]) if row else (False, {})


async def add_afk(user_id: int, mode):
    await execute(
        "INSERT INTO kk_afk_users (user_id, reason) VALUES ($1, $2) "
        "ON CONFLICT (user_id) DO UPDATE SET reason = EXCLUDED.reason",
        user_id,
        mode,
    )


async def remove_afk(user_id: int):
    row = await fetchrow("SELECT user_id FROM kk_afk_users WHERE user_id = $1", user_id)
    if row:
        await execute("DELETE FROM kk_afk_users WHERE user_id = $1", user_id)


async def get_afk_users() -> list:
    rows = await fetch("SELECT user_id, reason FROM kk_afk_users WHERE user_id > 0")
    return [dict(r) for r in rows]
