"""Gửi log về kênh log (LOG_CHANNEL) nhanh và không chặn handler.

Vấn đề cũ: mọi chỗ gửi log đều `await` trực tiếp, mà lỗi còn ghi file
rồi upload document + tải ảnh ngoài — nên log về kênh rất chậm và làm
chậm luôn cả lệnh đang chạy. Giờ log được gửi fire-and-forget qua
asyncio.create_task: lệnh trả lời người dùng ngay, log bay về kênh
ngay sau đó. Lỗi gửi log không bao giờ làm hỏng handler.
"""
import asyncio
from datetime import datetime, timezone
from logging import getLogger

from kaitokid.vars import LOG_CHANNEL

LOGGER = getLogger("KaitoKid")


def vn_now() -> str:
    """Giờ VN dạng 28/11/2026 20:45:12."""
    tz = timezone.utc
    try:
        from zoneinfo import ZoneInfo

        tz = ZoneInfo("Asia/Ho_Chi_Minh")
    except Exception:
        pass
    return datetime.now(tz).strftime("%d/%m/%Y %H:%M:%S")


async def _send_log(client, text: str) -> None:
    try:
        await client.send_message(
            LOG_CHANNEL, text, disable_web_page_preview=True
        )
    except Exception as e:
        LOGGER.warning(f"Không gửi được log về kênh: {e}")


def send_log(client, text: str) -> None:
    """Gửi log về kênh ngay, không chờ (fire-and-forget)."""
    try:
        asyncio.create_task(_send_log(client, text))
    except Exception as e:
        LOGGER.warning(f"Không tạo được task gửi log: {e}")


def log_block(title: str, lines: list[str]) -> str:
    """Đóng gói log thành 1 blockquote gọn, đẹp, có giờ VN."""
    body = "\n".join(lines)
    return (
        f"<blockquote expandable>{title}\n{body}\n"
        f"🕐 {vn_now()}</blockquote>"
    )
