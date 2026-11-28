import os
import re
import logging
from logging import getLogger
from asyncio import gather

from pyrogram.types import Message
from pySmartDL import SmartDL

from kaitokid import app
from kaitokid.core.decorator import new_task
from kaitokid.helper.functions import get_sender
from kaitokid.helper.localization import use_chat_lang

LOGGER = getLogger("KaitoKid")

__MODULE__ = "ChụpWeb"
__HELP__ = """
<blockquote>/webss [URL] - Chụp ảnh màn hình một trang Web.</blockquote>
"""

_DOMAIN_RE = re.compile(r"[A-Za-z0-9-]+(\.[A-Za-z0-9-]+)+(:\d+)?")


def _is_valid_url_or_domain(raw: str) -> bool:
    """Chỉ nhận link http(s)://... hoặc tên miền (vd google.com).

    Trả về False nếu có khoảng trắng hoặc domain không hợp lệ.
    """
    s = raw.strip()
    if not s or " " in s:
        return False
    rest = re.sub(r"^https?://", "", s, flags=re.I)
    rest = rest.split("/")[0].split("?")[0].split("#")[0]
    return bool(_DOMAIN_RE.fullmatch(rest))


@app.on_cmd("webss")
@new_task
@use_chat_lang()
async def take_ss(_, ctx: Message, strings):
    if len(ctx.command) == 1:
        return await ctx.reply_msg(strings("no_url"))
    raw = ctx.command[1].strip()
    if not _is_valid_url_or_domain(raw):
        return await ctx.reply_msg(strings("bad_url").format(url=raw))
    url = raw if raw.startswith("http") else f"https://{raw}"
    # Người gửi có thể là acc thường, bot hoặc kênh.
    sender_id, _ = get_sender(ctx)
    if sender_id is None:
        return
    download_file_path = os.path.join("downloads/", f"webSS_{abs(sender_id)}.png")
    msg = await ctx.reply_msg(strings("wait_str"))
    try:
        url = f"https://webss.yasirweb.eu.org/api/screenshot?resX=1280&resY=900&outFormat=jpg&waitTime=1000&isFullPage=false&dismissModals=false&url={url}"
        downloader = SmartDL(
            url, download_file_path, progress_bar=False, timeout=15, verify=False
        )
        downloader.start(blocking=True)
        await gather(
            *[
                # ctx.reply_document(download_file_path),
                ctx.reply_photo(download_file_path, caption=strings("str_credit")),
            ]
        )
        await msg.delete_msg()
        if os.path.exists(download_file_path):
            os.remove(download_file_path)
    except Exception as e:
        LOGGER.warning(f"/webss thất bại ({raw}): {e}")
        await msg.edit_msg(strings("ss_failed_str").format(url=raw))
