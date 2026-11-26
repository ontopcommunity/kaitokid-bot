from typing import Dict, Union

from database import execute, fetch, fetchrow
from kaitokid.helper.functions import int_to_alpha


async def get_karmas_count() -> dict:
    chats_count = 0
    karmas_count = 0
    rows = await fetch(
        "SELECT karma FROM kk_karma WHERE chat_id < 0 AND is_toggle = FALSE"
    )
    for row in rows:
        for i in (row["karma"] or {}):
            karma_ = row["karma"][i]["karma"]
            if karma_ > 0:
                karmas_count += karma_
        chats_count += 1
    return {"chats_count": chats_count, "karmas_count": karmas_count}


async def user_global_karma(user_id) -> int:
    total_karma = 0
    rows = await fetch(
        "SELECT chat_id FROM kk_karma WHERE chat_id < 0 AND is_toggle = FALSE"
    )
    for row in rows:
        karma = await get_karma(row["chat_id"], await int_to_alpha(user_id))
        if karma and (int(karma["karma"]) > 0):
            total_karma += int(karma["karma"])
    return total_karma


async def get_karmas(chat_id: int) -> Dict[str, int]:
    row = await fetchrow(
        "SELECT karma FROM kk_karma WHERE chat_id = $1 AND is_toggle = FALSE", chat_id
    )
    return dict(row["karma"]) if row else {}


async def get_karma(chat_id: int, name: str) -> Union[bool, dict]:
    name = name.lower().strip()
    karmas = await get_karmas(chat_id)
    if name in karmas:
        return karmas[name]
    return False


async def update_karma(chat_id: int, name: str, karma: dict):
    name = name.lower().strip()
    karmas = await get_karmas(chat_id)
    karmas[name] = karma
    await execute(
        "INSERT INTO kk_karma (chat_id, is_toggle, karma) VALUES ($1, FALSE, $2) "
        "ON CONFLICT (chat_id, is_toggle) DO UPDATE SET karma = EXCLUDED.karma",
        chat_id,
        karmas,
    )


async def is_karma_on(chat_id: int) -> bool:
    row = await fetchrow(
        "SELECT 1 FROM kk_karma WHERE chat_id = $1 AND is_toggle = TRUE", chat_id
    )
    return not row


async def karma_on(chat_id: int):
    is_karma = await is_karma_on(chat_id)
    if is_karma:
        return
    await execute(
        "DELETE FROM kk_karma WHERE chat_id = $1 AND is_toggle = TRUE", chat_id
    )


async def karma_off(chat_id: int):
    is_karma = await is_karma_on(chat_id)
    if not is_karma:
        return
    await execute(
        "INSERT INTO kk_karma (chat_id, is_toggle, karma) VALUES ($1, TRUE, '{}'::jsonb) "
        "ON CONFLICT DO NOTHING",
        chat_id,
    )


async def reset_all_karma(chat_id: int):
    # Xóa toàn bộ điểm karma cho chat_id cụ thể
    await execute(
        "INSERT INTO kk_karma (chat_id, is_toggle, karma) VALUES ($1, FALSE, '{}'::jsonb) "
        "ON CONFLICT (chat_id, is_toggle) DO UPDATE SET karma = '{}'::jsonb",
        chat_id,
    )
