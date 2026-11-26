from typing import Union
from datetime import datetime, timedelta, timezone

from database import execute, fetchrow


async def get_user_command_usage(chat_id: int, user_id: int, command: str) -> Union[dict, bool]:
    """Kiểm tra lần sử dụng gần nhất của người dùng với lệnh cụ thể."""
    row = await fetchrow(
        "SELECT chat_id, user_id, command, last_used FROM kk_funny "
        "WHERE chat_id = $1 AND user_id = $2 AND command = $3",
        chat_id,
        user_id,
        command,
    )
    return dict(row) if row else False


async def update_user_command_usage(chat_id: int, user_id: int, command: str):
    """Cập nhật hoặc ghi lại lần sử dụng lệnh của người dùng."""
    await execute(
        "INSERT INTO kk_funny (chat_id, user_id, command, last_used) "
        "VALUES ($1, $2, $3, $4) "
        "ON CONFLICT (chat_id, user_id, command) DO UPDATE SET last_used = EXCLUDED.last_used",
        chat_id,
        user_id,
        command,
        datetime.now(timezone.utc),
    )


async def can_use_command(chat_id: int, user_id: int, command: str) -> bool:
    """Kiểm tra xem người dùng có thể sử dụng lệnh hay không (chưa dùng trong ngày)."""
    usage = await get_user_command_usage(chat_id, user_id, command)
    if not usage:
        return True
    last_used = usage["last_used"]
    # Kiểm tra xem đã qua 24 giờ chưa
    if datetime.now(timezone.utc) - last_used >= timedelta(days=1):
        return True
    return False


async def reset_user_command_usage(chat_id: int, user_id: int):
    """Xóa dữ liệu sử dụng lệnh của người dùng trong chat cụ thể."""
    await execute(
        "DELETE FROM kk_funny WHERE chat_id = $1 AND user_id = $2", chat_id, user_id
    )
