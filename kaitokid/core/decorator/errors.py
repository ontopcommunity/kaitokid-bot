import traceback
from functools import wraps

from pyrogram.errors.exceptions.forbidden_403 import ChatWriteForbidden
from pyrogram.types import CallbackQuery

from kaitokid.helper.log_channel import log_block, send_log


def capture_err(func):
    @wraps(func)
    async def capture(client, message, *args, **kwargs):
        if isinstance(message, CallbackQuery):
            sender = message.message.reply
            chat = message.message.chat
            msg = message.message.text or message.message.caption
        else:
            sender = message.reply
            chat = message.chat
            msg = message.text or message.caption
        try:
            return await func(client, message, *args, **kwargs)
        except ChatWriteForbidden:
            return await client.leave_chat(message.chat.id)
        except Exception as err:
            exc = traceback.format_exc()
            # Gửi log về kênh ngay (text, không ghi file/upload cho nhanh).
            who = (
                message.from_user.id
                if message.from_user
                else (message.sender_chat.id if getattr(message, "sender_chat", None) else 0)
            )
            send_log(
                client,
                log_block(
                    "🚨 <b>BOT GẶP LỖI</b>",
                    [
                        f"👤 Người dùng: <code>{who}</code>",
                        f"💬 Nhóm: <code>{chat.id if chat else 0}</code>",
                        f"📩 Lệnh: <code>{(msg or '')[:200]}</code>",
                        f"❌ Lỗi: <code>{exc[-1500:]}</code>",
                    ],
                ),
            )
            await sender(
                "😭 Bot gặp lỗi khi xử lý lệnh của bạn, mình đã gửi nhật ký cho admin rồi. Xin lỗi vì sự bất tiện này..."
            )
            raise err

    return capture
