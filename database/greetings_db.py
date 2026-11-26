from database import execute, fetchrow


# Chức năng chào mừng
async def is_welcome(chat_id: int) -> bool:
    row = await fetchrow(
        "SELECT welcome_enabled FROM kk_greetings WHERE chat_id = $1", chat_id
    )
    return bool(row and row["welcome_enabled"])


async def toggle_welcome(chat_id: int):
    row = await fetchrow(
        "SELECT welcome_enabled FROM kk_greetings WHERE chat_id = $1", chat_id
    )
    if row and row["welcome_enabled"]:
        await execute(
            "UPDATE kk_greetings SET welcome_enabled = FALSE WHERE chat_id = $1",
            chat_id,
        )
        return False
    else:
        await execute(
            "INSERT INTO kk_greetings (chat_id, welcome_enabled) VALUES ($1, TRUE) "
            "ON CONFLICT (chat_id) DO UPDATE SET welcome_enabled = TRUE",
            chat_id,
        )
        return True


async def set_custom_welcome(chat_id: int, custom_message: str, buttons: list = None):
    await execute(
        "INSERT INTO kk_greetings (chat_id, welcome_enabled, custom_welcome_message, welcome_buttons) "
        "VALUES ($1, TRUE, $2, $3) "
        "ON CONFLICT (chat_id) DO UPDATE SET welcome_enabled = TRUE, "
        "custom_welcome_message = EXCLUDED.custom_welcome_message, "
        "welcome_buttons = EXCLUDED.welcome_buttons",
        chat_id,
        custom_message,
        buttons or [],
    )


async def get_custom_welcome(chat_id: int):
    row = await fetchrow(
        "SELECT custom_welcome_message, welcome_buttons FROM kk_greetings WHERE chat_id = $1",
        chat_id,
    )
    if row and row["custom_welcome_message"] is not None:
        return row["custom_welcome_message"], list(row["welcome_buttons"] or [])
    return None, []


# Chức năng cấm tự động khi rời nhóm
async def is_ban_on_leave(chat_id: int) -> bool:
    row = await fetchrow(
        "SELECT ban_on_leave_enabled FROM kk_greetings WHERE chat_id = $1", chat_id
    )
    return bool(row and row["ban_on_leave_enabled"])


async def toggle_ban_on_leave(chat_id: int):
    row = await fetchrow(
        "SELECT ban_on_leave_enabled FROM kk_greetings WHERE chat_id = $1", chat_id
    )
    if row and row["ban_on_leave_enabled"]:
        await execute(
            "UPDATE kk_greetings SET ban_on_leave_enabled = FALSE WHERE chat_id = $1",
            chat_id,
        )
        return False
    else:
        await execute(
            "INSERT INTO kk_greetings (chat_id, ban_on_leave_enabled) VALUES ($1, TRUE) "
            "ON CONFLICT (chat_id) DO UPDATE SET ban_on_leave_enabled = TRUE",
            chat_id,
        )
        return True
