from typing import Iterable

from pyrogram.enums import ChatType

from database import execute, fetchrow

group_types: Iterable[ChatType] = (ChatType.GROUP, ChatType.SUPERGROUP)


async def set_db_lang(chat_id: int, chat_type: str, lang_code: str):
    await execute(
        "INSERT INTO kk_locale (chat_id, lang, chat_type) VALUES ($1, $2, $3) "
        "ON CONFLICT (chat_id) DO UPDATE SET lang = EXCLUDED.lang, "
        "chat_type = EXCLUDED.chat_type",
        chat_id,
        lang_code,
        chat_type.value,
    )


async def get_db_lang(chat_id: int) -> str:
    row = await fetchrow("SELECT lang FROM kk_locale WHERE chat_id = $1", chat_id)
    return row["lang"] if row else {}
