import asyncio
import logging
from logging import getLogger

from pyrogram import Client, enums
from pyrogram.types import Message

from kaitokid import app
from kaitokid.core.decorator import new_task

LOGGER = getLogger("KaitoKid")
LOGGER. setLevel(logging.INFO)

__MODULE__ = "TròChơi"
__HELP__ = """
<blockquote>Chơi trò chơi với các biểu tượng cảm xúc:
/dice - Xúc xắc 🎲
/tungxu - Đồng xu 🪙
/dart - Phi tiêu 🎯
/basket - Bóng rổ 🏀
/ball - Bóng bowling 🎳
/football - Bóng đá ⚽
/jackpot - Máy đánh bạc 🎰</blockquote>
<blockquote>🎮 Mini game (người chơi mới được cấp 500.000):
/trochoi - Menu chọn trò
/tx - Tài xỉu 🎲 (vd: /tx tài 5k; thắng x3, cược tối thiểu 5.000, viết tắt 5k/1m/1b)
/bc - Bầu cua tôm cá 🦀
/noitu - Nối từ 🔤 (mỗi câu đúng +5% số dư)
/lucky - Vòng xoay may mắn 🎡
/sodu - Xem số dư 💰
/bxh - Bảng xếp hạng số tiền 🏆
/gift - Tặng tiền 🎁 (vd: /gift @username 1000)</blockquote>
"""

@app.on_cmd("dice")
@new_task
async def dice(self: Client, ctx: Message):
    try:
        x = await self.send_dice(ctx.chat.id, reply_to_message_id=ctx.id)
        m = x.dice.value
        await ctx.reply_msg(
            f"Xin chào {ctx.from_user.mention if ctx.from_user else ctx.sender_chat.title}, điểm của bạn là: {m}",
            quote=True
        )
    except Exception as e:
        LOGGER.error(f"Error in /dice: {str(e)}")
        await ctx.reply_msg(f"Lỗi: {str(e)}", quote=True)

@app.on_cmd("dart")
@new_task
async def dart(self: Client, ctx: Message):
    try:
        x = await self.send_dice(ctx.chat.id, "🎯", reply_to_message_id=ctx.id)
        m = x.dice.value
        await ctx.reply_msg(
            f"Xin chào {ctx.from_user.mention if ctx.from_user else ctx.sender_chat.title}, điểm của bạn là: {m}",
            quote=True
        )
    except Exception as e:
        LOGGER.error(f"Error in /dart: {str(e)}")
        await ctx.reply_msg(f"Lỗi: {str(e)}", quote=True)

@app.on_cmd("basket")
@new_task
async def basket(self: Client, ctx: Message):
    try:
        x = await self.send_dice(ctx.chat.id, "🏀", reply_to_message_id=ctx.id)
        m = x.dice.value
        await ctx.reply_msg(
            f"Xin chào {ctx.from_user.mention if ctx.from_user else ctx.sender_chat.title}, điểm của bạn là: {m}",
            quote=True
        )
    except Exception as e:
        LOGGER.error(f"Error in /basket: {str(e)}")
        await ctx.reply_msg(f"Lỗi: {str(e)}", quote=True)

@app.on_cmd("jackpot")
@new_task
async def jackpot(self: Client, ctx: Message):
    try:
        x = await self.send_dice(ctx.chat.id, "🎰", reply_to_message_id=ctx.id)
        m = x.dice.value
        await ctx.reply_msg(
            f"Xin chào {ctx.from_user.mention if ctx.from_user else ctx.sender_chat.title}, điểm của bạn là: {m}",
            quote=True
        )
    except Exception as e:
        LOGGER.error(f"Error in /jackpot: {str(e)}")
        await ctx.reply_msg(f"Lỗi: {str(e)}", quote=True)

@app.on_cmd("ball")
@new_task
async def ball(self: Client, ctx: Message):
    try:
        x = await self.send_dice(ctx.chat.id, "🎳", reply_to_message_id=ctx.id)
        m = x.dice.value
        await ctx.reply_msg(
            f"Xin chào {ctx.from_user.mention if ctx.from_user else ctx.sender_chat.title}, điểm của bạn là: {m}",
            quote=True
        )
    except Exception as e:
        LOGGER.error(f"Error in /ball: {str(e)}")
        await ctx.reply_msg(f"Lỗi: {str(e)}", quote=True)

@app.on_cmd("football")
@new_task
async def football(self: Client, ctx: Message):
    try:
        x = await self.send_dice(ctx.chat.id, "⚽", reply_to_message_id=ctx.id)
        m = x.dice.value
        await ctx.reply_msg(
            f"Xin chào {ctx.from_user.mention if ctx.from_user else ctx.sender_chat.title}, điểm của bạn là: {m}",
            quote=True
        )
    except Exception as e:
        LOGGER.error(f"Error in /football: {str(e)}")
        await ctx.reply_msg(f"Lỗi: {str(e)}", quote=True)