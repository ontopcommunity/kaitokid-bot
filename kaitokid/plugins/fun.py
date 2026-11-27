import textwrap
from asyncio import gather
import asyncio
import logging
import os
import random
import uuid
import tempfile
from logging import getLogger
from pyrogram import filters
from pyrogram.errors import MessageIdInvalid, PeerIdInvalid, ReactionInvalid
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup, CallbackQuery
from kaitokid import app, user
from kaitokid.core.decorator.errors import capture_err
from kaitokid.helper.localization import use_chat_lang
from kaitokid.vars import COMMAND_HANDLER, SUDO


        
@app.on_message(filters.command(["tungxx"], COMMAND_HANDLER))
@use_chat_lang()
async def dice(c, m, strings):
    dices = await c.send_dice(m.chat.id, reply_to_message_id=m.id)
    await dices.reply_msg(strings("result").format(number=dices.dice.value), quote=True)


@app.on_message(filters.command(["anony"], COMMAND_HANDLER))
async def beriharapan(c, m):
    reply = m.reply_to_message

    # Kiểm tra nếu không có tin nhắn được trả lời hoặc không có nội dung sau lệnh
    if not reply:
        return await m.reply("Hãy trả lời một tin nhắn để thực hiện lệnh này.")

    if len(m.text.split(maxsplit=1)) < 2:
        return await m.reply("Hãy nhập tin nhắn sau lệnh /anony.")

    pesan = m.text.split(maxsplit=1)[1]
    if reply.from_user:
        reply_name = reply.from_user.mention
    elif reply.sender_chat:
        reply_name = reply.sender_chat.title
    else:
        return await m.reply("Không thể xác định người nhận.")

    sender_name = m.from_user.mention if m.from_user else m.sender_chat.title
    await reply.reply(f"{pesan}\n\nĐược ai đó gửi tới {reply_name}")


@app.on_message(filters.command("react", COMMAND_HANDLER) & filters.user(SUDO))
@user.on_message(filters.command("react", COMMAND_HANDLER))
async def givereact(c, m):
    if len(m.command) == 1:
        return await m.reply(
            "Vui lòng thêm phản ứng sau lệnh, bạn cũng có thể đưa ra nhiều phản ứng."
        )
    if not m.reply_to_message:
        return await m.reply("Vui lòng trả lời tin nhắn bạn muốn phản hồi.")
    emot = list(regex.findall(r"\p{Emoji}", m.text))
    try:
        await m.reply_to_message.react(emoji=emot)
    except ReactionInvalid:
        await m.reply("Hãy đưa ra phản ứng chính xác.")
    except MessageIdInvalid:
        await m.reply(
            "Xin lỗi, tôi không thể phản ứng với các bot khác hoặc không có tư cách quản trị viên."
        )
    except PeerIdInvalid:
        await m.reply("Xin lỗi, tôi không thể phản hồi trò chuyện nếu không tham gia nhóm đó.")
    except Exception as err:
        await m.reply(str(err))


# @app.on_message_reaction_updated(filters.chat(-1005709128483))
async def reaction_update(self, ctx):
    self.log.info(ctx)

# Đường dẫn tới file GIF
GIF_PATH = "/www/wwwroot/tiensi-teo-bot/assets/tungxu.gif"

# Hàm xử lý khi người dùng gõ lệnh /coin
@app.on_message(filters.command("tungxu", COMMAND_HANDLER))
async def coin_flip_command(client, message):
    user_id = message.from_user.id
    
    # Kiểm tra nội dung sau lệnh /coin
    try:
        user_input = message.text.split(maxsplit=1)[1].lower()  # Lấy phần nội dung sau /coin
    except IndexError:
        await message.reply("Bạn phải nhập 'sấp' hoặc 'ngửa' sau lệnh /tungxu. Ví dụ: /tungxu sấp")
        return

    # Kiểm tra xem có chứa "sấp" hoặc "ngửa"
    if "sấp" not in user_input and "ngửa" not in user_input:
        await message.reply("Sai cú pháp! Bạn phải nhập 'sấp' hoặc 'ngửa'. Ví dụ: /tungxu tôi đoán sấp")
        return

    # Xác định dự đoán
    guess = "sấp" if "sấp" in user_input else "ngửa"

    # Tạo nút "Tung luôn" và đính kèm ID người dùng
    buttons = InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("Tung luôn", callback_data=f"flip:{user_id}")]
        ]
    )
    reply_message = await message.reply(f"💰 Bạn đã đoán là xu sẽ {guess}. Nhấn nút bên để tung đồng xu!", reply_markup=buttons)

# Hàm xử lý khi bấm nút "Tung xu"
@app.on_callback_query(filters.regex(r"flip:(\d+)"))
async def coin_flip_callback(client, callback_query: CallbackQuery):
    user_id = int(callback_query.data.split(":")[1])
    
    # Kiểm tra nếu người bấm nút là người ra lệnh
    if callback_query.from_user.id != user_id:
        await callback_query.answer("Bạn không thể tung vì không phải người cược!", show_alert=True)
        return

    # Cập nhật tin nhắn gốc để hiển thị trạng thái "Đang tung xu"
    await callback_query.edit_message_text("🎲 Đang tung đồng xu cho bạn...", reply_markup=None)

    # Gửi GIF "tung xu" và reply vào tin nhắn gốc (tin nhắn có nút bấm)
    gif_message = await callback_query.message.reply_animation(
        animation=GIF_PATH
    )
    
    # Hiệu ứng chờ trong 3 giây
    await asyncio.sleep(3)

    # Tung đồng xu (sấp hoặc ngửa)
    result = random.choice(["🪙 Sấp", "🪙 Ngửa"])

    # Xóa GIF sau khi đã chờ xong
    await gif_message.delete()

    # Chỉnh sửa tin nhắn gốc (tin nhắn chứa nút bấm) để hiển thị kết quả
    await callback_query.edit_message_text(f"💥 Kết quả sau khi tung đồng xu: {result}", reply_markup=None)

    
# Danh sách các câu trả lời ngẫu nhiên
responses = [
    "Ai gọi KaitoKid đấy? 🧐",
    "Nhắc đến KaitoKid làm gì thế? 😎",
    "KaitoKid ở đây, ai cần gì nào? 🙌",
    "KaitoKid không muốn xuất hiện đâu nhé! 😅",
    "Bạn vừa gọi KaitoKid, đừng nói là không! 🤔",
    "Hình như có ai đó nhắc đến KaitoKid? 👀",
    "Gọi KaitoKid có việc gì không, hay chỉ muốn vui chơi? 😄",
    "KaitoKid đã nghe thấy tiếng gọi từ xa! 📞",
    "Ồ, KaitoKid được gọi lên sân khấu à? 🎤",
    "KaitoKid đang ngủ, ai lại làm phiền thế này! 😴",
    "KaitoKid đây! Muốn gì nào, bạn ơi? 😊",
    "KaitoKid xuất hiện trong một cuộc gọi bí ẩn... 👻",
    "KaitoKid nghe rõ, sao cơ? 🎧",
    "Lại là KaitoKid, chắc có chuyện gì hệ trọng! 😳",
    "Bạn vừa nhắc đến KaitoKid hả? Cẩn thận đó! 🤨",
    "KaitoKid sắp bùng nổ vì bị gọi quá nhiều rồi! 💥",
    "Ai lại đang tìm KaitoKid lừng danh vậy? 🕵️",
    "Gọi KaitoKid một phát, chắc chắn có điều bí ẩn! 🔍",
    "Nhắc đến KaitoKid là phải cẩn trọng nhé! ⚠️",
    "KaitoKid có mặt, có ai cần được giúp đỡ không? 🦸",
    "Bạn vừa khơi mào một cuộc phiêu lưu của KaitoKid! 🗺️",
    "Chào mừng đến với thế giới của KaitoKid! 🌍",
    "Có ai đang nhắc đến một huyền thoại tên KaitoKid không? 🌟",
    "Gọi KaitoKid thế này, chắc lại có chuyện lớn rồi! 🚨",
    "Bạn đã đánh thức con quái vật KaitoKid! 🐉",
    "KaitoKid nghe thấy tiếng gọi từ vũ trụ xa xôi! 🌌",
    "Đừng có mà đùa với KaitoKid nhé! 🤡",
    "KaitoKid vừa nghe thấy một tiếng gọi rất lạ... 👽",
    "KaitoKid đây, ai gọi thế? 🤗",
    "Gọi KaitoKid thì phải có lý do chính đáng nhé! 📝",
    "Một lời nhắc đến KaitoKid có thể làm rung chuyển thế giới! 🌪️"
]


# Hàm xử lý khi phát hiện từ 'KaitoKid' trong tin nhắn
@app.on_message(filters.text & filters.regex(r".*KaitoKid.*"))
@use_chat_lang()
async def reply_to_teo(c, m, strings):
    response = random.choice(responses)  # Chọn câu trả lời ngẫu nhiên
    await c.send_message(m.chat.id, response, reply_to_message_id=m.id)
