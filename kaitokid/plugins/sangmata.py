import logging
from logging import getLogger
from pyrogram import filters
from pyrogram.types import Message

from database.sangmata_db import (
    add_userdata,
    cek_userdata,
    get_userdata,
    is_sangmata_on,
    sangmata_off,
    sangmata_on,
)
from kaitokid import app
from kaitokid.core.decorator.permissions import adminsOnly
from kaitokid.helper.localization import use_chat_lang
from kaitokid.vars import COMMAND_HANDLER

LOGGER = getLogger("KaitoKid")

__MODULE__ = "KiểmTraĐổiTên"
__HELP__ = """
<blockquote>Tính năng này được lấy cảm hứng từ Bot SangMata. Tôi đã tạo một hệ thống phát hiện đơn giản để kiểm tra dữ liệu người dùng bao gồm tên người dùng, first_name và last_name. Nó sẽ giúp bạn có thể biết ai đó đã đổi tên của họ gần đây.
/sangmata_set [on/off] - Bật/tắt sangmata trong các nhóm.</blockquote>
"""


# Check user that change first_name, last_name and usernaname
@app.on_message(
    filters.group & ~filters.bot & ~filters.via_bot,
    group=5,
)
@use_chat_lang()
async def cek_mataa(_, ctx: Message, strings):
    if ctx.sender_chat or not await is_sangmata_on(ctx.chat.id):
        return
    if not await cek_userdata(ctx.from_user.id):
        return await add_userdata(
            ctx.from_user.id,
            ctx.from_user.username,
            ctx.from_user.first_name,
            ctx.from_user.last_name,
        )
    usernamebefore, first_name, lastname_before = await get_userdata(ctx.from_user.id)
    msg = ""
    if (
        usernamebefore != ctx.from_user.username
        or first_name != ctx.from_user.first_name
        or lastname_before != ctx.from_user.last_name
    ):
        msg += f"👀 <b>KaitoKid Check</b>\n\n🌞 Người dùng: {ctx.from_user.mention} [<code>{ctx.from_user.id}</code>]\n"
    if usernamebefore != ctx.from_user.username:
        usernamebefore = f"@{usernamebefore}" if usernamebefore else strings("no_uname")
        usernameafter = (
            f"@{ctx.from_user.username}"
            if ctx.from_user.username
            else strings("no_uname")
        )
        msg += strings("uname_change_msg").format(bef=usernamebefore, aft=usernameafter)
        await add_userdata(
            ctx.from_user.id,
            ctx.from_user.username,
            ctx.from_user.first_name,
            ctx.from_user.last_name,
        )
    if first_name != ctx.from_user.first_name:
        msg += strings("firstname_change_msg").format(
            bef=first_name, aft=ctx.from_user.first_name
        )
        await add_userdata(
            ctx.from_user.id,
            ctx.from_user.username,
            ctx.from_user.first_name,
            ctx.from_user.last_name,
        )
    if lastname_before != ctx.from_user.last_name:
        lastname_before = lastname_before or strings("no_last_name")
        lastname_after = ctx.from_user.last_name or strings("no_last_name")
        msg += strings("lastname_change_msg").format(
            bef=lastname_before, aft=lastname_after
        )
        await add_userdata(
            ctx.from_user.id,
            ctx.from_user.username,
            ctx.from_user.first_name,
            ctx.from_user.last_name,
        )
    if msg != "":
        await ctx.reply_msg(msg, quote=False)


@app.on_message(
    filters.group
    & filters.command("sangmata_set", COMMAND_HANDLER)
    & ~filters.bot
    & ~filters.via_bot
)
@adminsOnly("can_change_info")
@use_chat_lang()
async def set_mataa(_, ctx: Message, strings):
    if len(ctx.command) == 1:
        return await ctx.reply_msg(
            strings("set_sangmata_help").format(cmd=ctx.command[0]), del_in=6
        )
    if ctx.command[1] == "on":
        cekset = await is_sangmata_on(ctx.chat.id)
        if cekset:
            await ctx.reply_msg(strings("sangmata_already_on"))
        else:
            await sangmata_on(ctx.chat.id)
            await ctx.reply_msg(strings("sangmata_enabled"))
    elif ctx.command[1] == "off":
        cekset = await is_sangmata_on(ctx.chat.id)
        if not cekset:
            await ctx.reply_msg(strings("sangmata_already_off"))
        else:
            await sangmata_off(ctx.chat.id)
            await ctx.reply_msg(strings("sangmata_disabled"))
    else:
        await ctx.reply_msg(strings("wrong_param"), del_in=6)
