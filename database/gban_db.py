from database import execute, fetchrow


async def is_gbanned_user(user_id: int) -> bool:
    row = await fetchrow("SELECT user_id FROM kk_gban WHERE user_id = $1", user_id)
    return bool(row)


async def add_gban_user(user_id: int):
    is_gbanned = await is_gbanned_user(user_id)
    if is_gbanned:
        return
    await execute(
        "INSERT INTO kk_gban (user_id) VALUES ($1) ON CONFLICT DO NOTHING", user_id
    )


async def remove_gban_user(user_id: int):
    is_gbanned = await is_gbanned_user(user_id)
    if not is_gbanned:
        return
    await execute("DELETE FROM kk_gban WHERE user_id = $1", user_id)
