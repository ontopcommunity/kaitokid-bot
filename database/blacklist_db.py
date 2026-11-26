from typing import List

from database import execute, fetchrow


async def get_blacklisted_words(chat_id: int) -> List[str]:
    row = await fetchrow(
        "SELECT filters FROM kk_blacklist_filters WHERE chat_id = $1", chat_id
    )
    return [] if not row else list(row["filters"] or [])


async def save_blacklist_filter(chat_id: int, word: str):
    word = word.lower().strip()
    _filters = await get_blacklisted_words(chat_id)
    _filters.append(word)
    await execute(
        "INSERT INTO kk_blacklist_filters (chat_id, filters) VALUES ($1, $2) "
        "ON CONFLICT (chat_id) DO UPDATE SET filters = EXCLUDED.filters",
        chat_id,
        _filters,
    )


async def delete_blacklist_filter(chat_id: int, word: str) -> bool:
    filtersd = await get_blacklisted_words(chat_id)
    word = word.lower().strip()
    if word in filtersd:
        filtersd.remove(word)
        await execute(
            "INSERT INTO kk_blacklist_filters (chat_id, filters) VALUES ($1, $2) "
            "ON CONFLICT (chat_id) DO UPDATE SET filters = EXCLUDED.filters",
            chat_id,
            filtersd,
        )
        return True
    return False
