# tgEasy - Easy for a brighter Shine. A monkey pather add-on for Pyrogram
# Copyright (C) 2021 - 2022 Jayant Hegde Kageri <https://github.com/jayantkageri>

# This file is part of tgEasy.

# tgEasy is free software: you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License as published
# by the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# tgEasy is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Lesser General Public License for more details.

# You should have received a copy of the GNU Lesser General Public License
# along with tgEasy.  If not, see <http://www.gnu.org/licenses/>.
import contextlib
import logging
import traceback
import typing

import pyrogram

from kaitokid.log_channel import delete_after, log_block, send_log

LOGGER = logging.getLogger("KaitoKid")

_SORRY = (
    "😭 Bot gặp lỗi khi xử lý lệnh của bạn, "
    "mình đã gửi nhật ký cho admin rồi. Xin lỗi vì sự bất tiện này..."
)


async def handle_error(
    _, m: typing.Union[pyrogram.types.Message, pyrogram.types.CallbackQuery]
):
    """
    ### `handle_error`
    - A Function to Handle the Errors in Functions.
    - This Sends the Error Log to the Log Group and Replies Sorry Message for the Users.
    - This is Helper for all of the functions for handling the Errors.

    - Parameters:
      - error:
        - The Exceptation.

      - m (`pyrogram.types.Message` or `pyrogram.types.CallbackQuery`):
        - The Message or Callback Query where the Error occurred.

    """
    exc = traceback.format_exc()
    LOGGER.error(exc)
    # Log về kênh ngay bằng text (không ghi file, không upload, không
    # tải ảnh ngoài) để không làm chậm lệnh đang chạy.
    if isinstance(m, pyrogram.types.CallbackQuery):
        client = m.message._client
        chat = m.message.chat
        text = m.message.text or m.message.caption
        who = (
            m.from_user.id
            if m.from_user
            else (m.sender_chat.id if getattr(m, "sender_chat", None) else 0)
        )
    else:
        client = m._client
        chat = m.chat
        text = m.text or m.caption
        who = (
            m.from_user.id
            if m.from_user
            else (m.sender_chat.id if getattr(m, "sender_chat", None) else 0)
        )
    send_log(
        client,
        log_block(
            "🚨 <b>BOT GẶP LỖI</b>",
            [
                f"👤 Người dùng: <code>{who}</code>",
                f"💬 Nhóm: <code>{chat.id if chat else 0}</code>",
                f"📩 Lệnh: <code>{(text or '')[:200]}</code>",
                f"❌ Lỗi: <code>{exc[-1500:]}</code>",
            ],
        ),
    )
    if isinstance(m, pyrogram.types.Message):
        with contextlib.suppress(Exception):
            sent = await m.reply_msg(_SORRY)
            if sent:
                # Tin lỗi tự xóa sau 2 phút (cho mọi người).
                delete_after(m._client, sent.chat.id, sent.id)
    if isinstance(m, pyrogram.types.CallbackQuery):
        with contextlib.suppress(Exception):
            sent = await m.message.reply_msg(_SORRY)
            if sent:
                # Tin lỗi tự xóa sau 2 phút (cho mọi người).
                delete_after(m.message._client, sent.chat.id, sent.id)
    return True
