from typing import Dict, List, Union

from database import execute, fetchrow


async def _get_filters(chat_id: int) -> Dict[str, int]:
    row = await fetchrow("SELECT filters FROM kk_filters WHERE chat_id = $1", chat_id)
    return dict(row["filters"]) if row else {}


async def delete_filter(chat_id: int, name: str) -> bool:
    filtersd = await _get_filters(chat_id)
    name = name.lower().strip()
    if name in filtersd:
        del filtersd[name]
        await execute(
            "INSERT INTO kk_filters (chat_id, filters) VALUES ($1, $2) "
            "ON CONFLICT (chat_id) DO UPDATE SET filters = EXCLUDED.filters",
            chat_id,
            filtersd,
        )
        return True
    return False


async def deleteall_filters(chat_id: int):
    return await execute("DELETE FROM kk_filters WHERE chat_id = $1", chat_id)


async def get_filter(chat_id: int, name: str) -> Union[bool, dict]:
    name = name.lower().strip()
    _filters = await _get_filters(chat_id)
    return _filters[name] if name in _filters else False


async def get_filters_names(chat_id: int) -> List[str]:
    return list(await _get_filters(chat_id))


async def save_filter(chat_id: int, name: str, _filter: dict):
    name = name.lower().strip()
    _filters = await _get_filters(chat_id)
    _filters[name] = _filter
    await execute(
        "INSERT INTO kk_filters (chat_id, filters) VALUES ($1, $2) "
        "ON CONFLICT (chat_id) DO UPDATE SET filters = EXCLUDED.filters",
        chat_id,
        _filters,
    )
