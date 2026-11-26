from database import execute, fetchrow


async def is_imdbset(user_id: int) -> bool:
    row = await fetchrow("SELECT lang FROM kk_imdb WHERE user_id = $1", user_id)
    return (True, row["lang"]) if row else (False, {})


async def add_imdbset(user_id: int, lang):
    await execute(
        "INSERT INTO kk_imdb (user_id, lang) VALUES ($1, $2) "
        "ON CONFLICT (user_id) DO UPDATE SET lang = EXCLUDED.lang",
        user_id,
        lang,
    )


async def remove_imdbset(user_id: int):
    row = await fetchrow("SELECT user_id FROM kk_imdb WHERE user_id = $1", user_id)
    if row:
        await execute("DELETE FROM kk_imdb WHERE user_id = $1", user_id)
