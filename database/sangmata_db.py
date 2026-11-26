from database import execute, fetchrow


# Get Data User
async def cek_userdata(user_id: int) -> bool:
    row = await fetchrow("SELECT user_id FROM kk_sangmata WHERE user_id = $1", user_id)
    return bool(row)


async def get_userdata(user_id: int) -> bool:
    row = await fetchrow(
        "SELECT username, first_name, last_name FROM kk_sangmata WHERE user_id = $1",
        user_id,
    )
    return row["username"], row["first_name"], row["last_name"]


async def add_userdata(user_id: int, username, first_name, last_name):
    await execute(
        "INSERT INTO kk_sangmata (user_id, username, first_name, last_name) "
        "VALUES ($1, $2, $3, $4) "
        "ON CONFLICT (user_id) DO UPDATE SET username = EXCLUDED.username, "
        "first_name = EXCLUDED.first_name, last_name = EXCLUDED.last_name",
        user_id,
        username,
        first_name,
        last_name,
    )


async def is_sangmata_on(chat_id: int) -> bool:
    row = await fetchrow(
        "SELECT chat_id_toggle FROM kk_sangmata WHERE chat_id_toggle = $1", chat_id
    )
    return bool(row)


async def sangmata_on(chat_id: int) -> bool:
    await execute(
        "INSERT INTO kk_sangmata (chat_id_toggle) VALUES ($1) ON CONFLICT DO NOTHING",
        chat_id,
    )


async def sangmata_off(chat_id: int):
    await execute("DELETE FROM kk_sangmata WHERE chat_id_toggle = $1", chat_id)
