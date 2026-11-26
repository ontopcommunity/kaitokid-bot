from typing import Dict, List, Union

from database import execute, fetchrow


async def _get_notes(chat_id: int) -> Dict[str, int]:
    row = await fetchrow("SELECT notes FROM kk_notes WHERE chat_id = $1", chat_id)
    return dict(row["notes"]) if row else {}


async def delete_note(chat_id: int, name: str) -> bool:
    notesd = await _get_notes(chat_id)
    name = name.lower().strip()
    if name in notesd:
        del notesd[name]
        await execute(
            "INSERT INTO kk_notes (chat_id, notes) VALUES ($1, $2) "
            "ON CONFLICT (chat_id) DO UPDATE SET notes = EXCLUDED.notes",
            chat_id,
            notesd,
        )
        return True
    return False


async def get_note(chat_id: int, name: str) -> Union[bool, dict]:
    name = name.lower().strip()
    _notes = await _get_notes(chat_id)
    return _notes[name] if name in _notes else False


async def get_note_names(chat_id: int) -> List[str]:
    return list(await _get_notes(chat_id))


async def save_note(chat_id: int, name: str, note: dict):
    name = name.lower().strip()
    _notes = await _get_notes(chat_id)
    _notes[name] = note

    await execute(
        "INSERT INTO kk_notes (chat_id, notes) VALUES ($1, $2) "
        "ON CONFLICT (chat_id) DO UPDATE SET notes = EXCLUDED.notes",
        chat_id,
        _notes,
    )


async def deleteall_notes(chat_id: int):
    return await execute("DELETE FROM kk_notes WHERE chat_id = $1", chat_id)
