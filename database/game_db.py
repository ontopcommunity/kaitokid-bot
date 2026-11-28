"""Số dư trò chơi KaitoKid (tài xỉu, bầu cua, nối từ, vòng xoay, gift).

Mỗi người chơi lần đầu được cấp 500.000. Số dư lưu theo user_id
(âm = acc kênh đăng bằng kênh). Dùng chung cho mọi trò.
"""
from database import execute, fetch, fetchrow, fetchval

START_BALANCE = 500000


async def ensure_user(user_id: int) -> int:
    """Tạo tài khoản game nếu chưa có (500k), trả về số dư hiện tại."""
    row = await fetchrow(
        "INSERT INTO kk_game_balance (user_id, balance) VALUES ($1, $2) "
        "ON CONFLICT (user_id) DO NOTHING RETURNING balance",
        user_id,
        START_BALANCE,
    )
    if row:
        return row["balance"]
    return await fetchval(
        "SELECT balance FROM kk_game_balance WHERE user_id = $1", user_id
    )


async def get_balance(user_id: int) -> int:
    """Số dư hiện tại (tự tạo tài khoản 500k nếu là người chơi mới)."""
    return await ensure_user(user_id)


async def add_balance(user_id: int, delta: int) -> int:
    """Cộng/trừ số dư (atomic), trả về số dư mới."""
    await ensure_user(user_id)
    row = await fetchrow(
        "UPDATE kk_game_balance SET balance = balance + $2, "
        "updated_at = now() WHERE user_id = $1 RETURNING balance",
        user_id,
        delta,
    )
    return row["balance"]


async def transfer(sender_id: int, receiver_id: int, amount: int):
    """Chuyển tiền: trừ người gửi, cộng người nhận (1 transaction).

    Trả về (ok, lý_do, số_dư_người_gửi_mới, số_dư_người_nhận_mới).
    """
    if amount <= 0:
        return False, "Số tiền phải lớn hơn 0.", None, None
    if sender_id == receiver_id:
        return False, "Không thể tự tặng cho chính mình.", None, None
    sender_bal = await ensure_user(sender_id)
    if sender_bal < amount:
        return False, "Không đủ số dư để tặng.", sender_bal, None
    await ensure_user(receiver_id)
    await execute(
        "UPDATE kk_game_balance SET balance = balance - $2, "
        "updated_at = now() WHERE user_id = $1",
        sender_id,
        amount,
    )
    receiver_bal = await fetchval(
        "UPDATE kk_game_balance SET balance = balance + $2, "
        "updated_at = now() WHERE user_id = $1 RETURNING balance",
        receiver_id,
        amount,
    )
    sender_new = sender_bal - amount
    return True, "", sender_new, receiver_bal


async def top_balances(limit: int = 10):
    """Top người chơi giàu nhất (toàn bot)."""
    rows = await fetch(
        "SELECT user_id, balance FROM kk_game_balance "
        "ORDER BY balance DESC LIMIT $1",
        limit,
    )
    return [dict(r) for r in rows]


async def get_rank(user_id: int):
    """Hạng của người chơi (1 = giàu nhất), None nếu chưa có tài khoản."""
    row = await fetchrow(
        "SELECT COUNT(*) + 1 AS rank FROM kk_game_balance "
        "WHERE balance > (SELECT balance FROM kk_game_balance WHERE user_id = $1)",
        user_id,
    )
    if not row:
        return None
    exists = await fetchval(
        "SELECT 1 FROM kk_game_balance WHERE user_id = $1", user_id
    )
    return row["rank"] if exists else None
