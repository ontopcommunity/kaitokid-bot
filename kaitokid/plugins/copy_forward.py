import logging
from logging import getLogger

from pyrogram import enums, filters
from pyrogram.errors import UserIsBlocked, UserNotParticipant
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from kaitokid import BOT_USERNAME, app
from kaitokid.core.decorator.errors import capture_err
from kaitokid.helper.functions import get_sender
from kaitokid.vars import COMMAND_HANDLER

LOGGER = getLogger("KaitoKid")

@app.on_message(filters.command(["saochep"], COMMAND_HANDLER))
async def copymsg(_, message):
    if len(message.command) == 1:
        if not message.reply_to_message:
            return await message.reply("Vui lòng trả lời tin nhắn bạn muốn sao chép.")
        # Người gửi có thể là acc thường, bot hoặc kênh.
        sender_id, _ = get_sender(message)
        if sender_id is None:
            return
        try:
            await message.reply_to_message.copy(
                sender_id,
                caption_entities=message.reply_to_message.entities,
                reply_markup=message.reply_to_message.reply_markup,
            )
            return await message.reply_text("Tin nhắn đã được gửi thành công..")
        except UserIsBlocked:
            return await message.reply(
                "Vui lòng cho chủ nhân của tôi sao chép tin nhắn vào một cuộc trò chuyện riêng tư.",
                reply_markup=InlineKeyboardMarkup(
                    [
                        [
                            InlineKeyboardButton(
                                text="💬 Trò chuyện với tôi",
                                url=f"https://t.me/{BOT_USERNAME}",
                            )
                        ]
                    ]
                ),
            )
        except Exception as e:
            return await message.reply(f"ERROR: {str(e)}")

@app.on_message(filters.command(["chuyentiep"], COMMAND_HANDLER))
@capture_err
async def forwardmsg(_, message):
    if len(message.command) == 1:
        if not message.reply_to_message:
            return await message.reply("Vui lòng trả lời tin nhắn bạn muốn chuyển tiếp.")
        # Người gửi có thể là acc thường, bot hoặc kênh.
        sender_id, _ = get_sender(message)
        if sender_id is None:
            return
        try:
            await message.reply_to_message.forward(sender_id)
            return await message.reply_text("Tin nhắn đã được gửi thành công..")
        except UserIsBlocked:
            return await message.reply(
                "Vui lòng chuyển tiếp tin nhắn đến cuộc trò chuyện riêng tư của tôi..",
                reply_markup=InlineKeyboardMarkup(
                    [
                        [
                            InlineKeyboardButton(
                                text="💬 Trò chuyện với tôi",
                                url=f"https://t.me/{BOT_USERNAME}",
                            )
                        ]
                    ]
                ),
            )
        except Exception as e:
            return await message.reply(f"ERROR: {str(e)}")
