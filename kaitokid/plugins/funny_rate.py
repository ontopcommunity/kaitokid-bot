import random
import logging
from logging import getLogger
from datetime import datetime
from zoneinfo import ZoneInfo
from pyrogram import filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from kaitokid import app
from kaitokid.core.decorator.errors import capture_err
from kaitokid.helper.functions import get_sender
from kaitokid.vars import COMMAND_HANDLER, SUDO, TZ
from database.funny_db import get_daily_usage_count, increment_daily_usage

LOGGER = getLogger("KaitoKid")

__MODULE__ = "ĐánhGiáVui"
__HELP__ = """
<blockquote>/cutie - Đánh giá mức độ dễ thương của bạn hoặc người được trả lời.
/hot - Đánh giá mức độ nóng bỏng của bạn hoặc người được trả lời.
/horny - Đánh giá mức độ... tò mò của bạn hoặc người được trả lời.
/sexy - Đánh giá mức độ quyến rũ của bạn hoặc người được trả lời.
/gay - Đánh giá mức độ gay của bạn hoặc người được trả lời.
/lesbian - Đánh giá mức độ lesbian của bạn hoặc người được trả lời.
/boob - Đánh giá kích thước... của bạn hoặc người được trả lời.
/cock - Đánh giá kích thước... của bạn hoặc người được trả lời.</blockquote>
"""

# Định nghĩa các link media
MEDIA = {
    "cutie": "https://graph.org/file/24375c6e54609c0e4621c.mp4",
    "hot": "https://graph.org/file/745ba3ff07c1270958588.mp4",
    "horny": "https://graph.org/file/eaa834a1cbfad29bd1fe4.mp4",
    "sexy": "https://graph.org/file/58da22eb737af2f8963e6.mp4",
    "gay": "https://graph.org/file/850290f1f974c5421ce54.mp4",
    "lesbian": "https://graph.org/file/ff258085cf31f5385db8a.mp4",
    "boob": "https://i.gifer.com/8ZUg.gif",
    "cock": "https://telegra.ph/file/423414459345bf18310f5.gif"
}

# Nút hỗ trợ
BUTTON = [[InlineKeyboardButton("Ủng Hộ", url="https://t.me/sharecongngheontop")]]

# Giới hạn lượt đánh giá mỗi ngày (tính theo từng lệnh, theo giờ VN).
# Chủ bot (SUDO) không giới hạn; người khác tối đa 10 lượt/ngày/lệnh.
# Hết lượt: handler im lặng bỏ qua, bot không báo gì.
RATE_LIMIT = 10


def _rate_day():
    """Ngày hiện tại theo múi giờ của bot (mặc định giờ VN)."""
    return datetime.now(ZoneInfo(TZ)).date()


async def _is_unlimited(ctx, user_id: int) -> bool:
    """Admin không giới hạn lượt đánh giá: chủ bot (SUDO), admin nhóm,
    và acc dùng kênh để nhắn (ID âm — đăng bằng kênh là đã có quyền admin
    kênh đó nên cũng được miễn)."""
    if user_id in SUDO:
        return True
    if user_id < 0:
        # Kênh: không xác định được user đứng sau, mà đăng bằng kênh
        # thì đã là admin kênh — miễn giới hạn.
        return True
    try:
        member = await ctx.chat.get_member(user_id)
        return member.status.value in ("administrator", "creator")
    except Exception:
        return False


async def _can_rate(ctx, chat_id: int, user_id: int, command: str) -> bool:
    if await _is_unlimited(ctx, user_id):
        return True
    count = await get_daily_usage_count(chat_id, user_id, command, _rate_day())
    return count < RATE_LIMIT


async def _record_rate(ctx, chat_id: int, user_id: int, command: str):
    if await _is_unlimited(ctx, user_id):
        return
    await increment_daily_usage(chat_id, user_id, command, _rate_day())

# Hàm chung để xử lý các lệnh
async def handle_fun_command(ctx, command, caption_template, emoji):
    try:
        # Lấy thông tin người dùng (chạy cả acc thường, bot, acc dùng kênh).
        chat_id = ctx.chat.id
        sender_id, _ = get_sender(ctx)
        if sender_id is None:
            return
        if ctx.reply_to_message:
            user_id, user_name = get_sender(ctx.reply_to_message)
            if user_id is None:
                return
        else:
            user_id, user_name = sender_id, get_sender(ctx)[1]

        # Giới hạn lượt đánh giá: admin (chủ bot, admin nhóm, acc dùng kênh)
        # vô hạn; người khác tối đa 10 lượt/ngày. Hết lượt thì im lặng bỏ qua.
        if not await _can_rate(ctx, chat_id, sender_id, command):
            return

        # Kênh có ID âm: không link tg://user được, chỉ hiện tên.
        if user_id and user_id > 0:
            mention = f"[{user_name}](tg://user?id={user_id})"
        else:
            mention = user_name
        percentage = random.randint(1, 100)
        
        # Tùy chỉnh caption theo lệnh
        if command in ["boob", "cock"]:
            caption = caption_template.format(mention=mention, value=percentage)
        else:
            caption = caption_template.format(mention=mention, value=percentage)

        # Gửi media và caption
        await app.send_document(
            chat_id=ctx.chat.id,
            document=MEDIA[command],
            caption=caption,
            reply_markup=InlineKeyboardMarkup(BUTTON),
            reply_to_message_id=ctx.reply_to_message.id if ctx.reply_to_message else ctx.id
        )

        # Cập nhật dữ liệu sử dụng lệnh cho người gửi
        await _record_rate(ctx, chat_id, sender_id, command)

    except Exception as e:
        await ctx.reply_msg(f"Lỗi, vui lòng thử lại sau.", quote=True)

# Định nghĩa các lệnh
@app.on_message(filters.command(["cutie"], COMMAND_HANDLER))
@capture_err
async def cutie(_, ctx):
    await handle_fun_command(ctx, "cutie", "🍑 {mention} dễ thương {value}% nhé! 🥀", "🍑")

@app.on_message(filters.command(["hot"], COMMAND_HANDLER))
@capture_err
async def hot(_, ctx):
    await handle_fun_command(ctx, "hot", "🔥 {mention} nóng bỏng {value}%! 🔥", "🔥")

@app.on_message(filters.command(["horny"], COMMAND_HANDLER))
@capture_err
async def horny(_, ctx):
    await handle_fun_command(ctx, "horny", "🔥 {mention} tò mò {value}% nha! 😏", "🔥")

@app.on_message(filters.command(["sexy"], COMMAND_HANDLER))
@capture_err
async def sexy(_, ctx):
    await handle_fun_command(ctx, "sexy", "🔥 {mention} quyến rũ {value}%! 😘", "🔥")

@app.on_message(filters.command(["gay"], COMMAND_HANDLER))
@capture_err
async def gay(_, ctx):
    await handle_fun_command(ctx, "gay", "🍷 {mention} gay {value}% nè! 🏳️‍🌈", "🍷")

@app.on_message(filters.command(["lesbian"], COMMAND_HANDLER))
@capture_err
async def lesbian(_, ctx):
    await handle_fun_command(ctx, "lesbian", "💜 {mention} lesbian {value}% đó! 🏳️‍🌈", "💜")

@app.on_message(filters.command(["boob"], COMMAND_HANDLER))
@capture_err
async def boob(_, ctx):
    await handle_fun_command(ctx, "boob", "🍒 Kích thước ngực của {mention} là {value}! 😜", "🍒")

@app.on_message(filters.command(["cock"], COMMAND_HANDLER))
@capture_err
async def cock(_, ctx):
    await handle_fun_command(ctx, "cock", "🍆 Kích thước của {mention} là {value}cm! 😎", "🍆")