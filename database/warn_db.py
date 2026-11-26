from typing import Dict, Union

from database import execute, fetch, fetchrow


async def get_warns_count() -> dict:
    chats_count = 0
    warns_count = 0
    rows = await fetch("SELECT warns FROM kk_warns WHERE chat_id < 0")
    for row in rows:
        for user in (row["warns"] or {}):
            warns_count += row["warns"][user]["warns"]
        chats_count += 1
    return {"chats_count": chats_count, "warns_count": warns_count}


async def get_warns(chat_id: int) -> Dict[str, int]:
    row = await fetchrow("SELECT warns FROM kk_warns WHERE chat_id = $1", chat_id)
    return dict(row["warns"]) if row else {}


async def get_warn(chat_id: int, name: str) -> Union[bool, dict]:
    name = name.lower().strip()
    warns = await get_warns(chat_id)
    if name in warns:
        return warns[name]


async def add_warn(chat_id: int, name: str, warn: dict):
    name = name.lower().strip()
    warns = await get_warns(chat_id)
    warns[name] = warn

    await execute(
        "INSERT INTO kk_warns (chat_id, warns) VALUES ($1, $2) "
        "ON CONFLICT (chat_id) DO UPDATE SET warns = EXCLUDED.warns",
        chat_id,
        warns,
    )


async def remove_warns(chat_id: int, name: str) -> bool:
    warnsd = await get_warns(chat_id)
    name = name.lower().strip()
    if name in warnsd:
        del warnsd[name]
        await execute(
            "INSERT INTO kk_warns (chat_id, warns) VALUES ($1, $2) "
            "ON CONFLICT (chat_id) DO UPDATE SET warns = EXCLUDED.warns",
            chat_id,
            warnsd,
        )
        return True
    return False
