"""
Media Downloader — dán link là bot gửi nhạc/video.

- Link SoundCloud -> lấy info + file nhạc qua API apisynthesis
  (repo ontopcommunity/apisynthesis, deploy apisynthesis.vercel.app).
- Link TikTok -> lấy info + video không watermark qua API repo Tiktok
  (repo ontopcommunity/Tiktok, deploy tiktokvippro.vercel.app).
- Link video nền tảng khác (YouTube, Instagram, Facebook, X, ...) ->
  tải video qua API studiointernet (repo ontopcommunity/studiointernet-,
  deploy superinternetapi.vercel.app, backend gendownload.com) — lấy
  link stream chất lượng cao nhất rồi tải về gửi. yt-dlp chỉ còn là
  fallback khi API lỗi.
- /tiktok {username} -> thông tin tài khoản TikTok.

Toàn bộ caption đều dùng định dạng trích dẫn (blockquote) + nút
inline "Mở link" dẫn tới link gốc.
"""

import asyncio
import html
import logging
from logging import getLogger
import os
import re
import shutil
import tempfile
from pathlib import Path
from urllib.parse import quote, urlparse

import aiohttp
from pyrogram import enums, filters
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Message

from kaitokid import app
from kaitokid.core.decorator.errors import capture_err
from kaitokid.vars import COMMAND_HANDLER

LOGGER = getLogger("KaitoKid")

__MODULE__ = "TảiNhạcVideo"
__HELP__ = """
<blockquote>🎵 <b>Tải nhạc & video bằng link</b>
Dán link SoundCloud -> bot gửi file nhạc kèm tên bài + tác giả.
Dán link TikTok -> bot gửi video không watermark kèm thông tin video.
Dán link YouTube / Facebook / Instagram / X / ... -> bot gửi video chất lượng cao.
<b>/tiktok {username}</b> - Xem thông tin tài khoản TikTok.

Mọi lệnh đều chạy được với cả 3 đầu / . ! (ví dụ: /tiktok, .tiktok, !tiktok).</blockquote>
"""

APISYNTHESIS_BASE = "https://apisynthesis.vercel.app/api"
TIKTOK_API_BASE = "https://tiktokvippro.vercel.app/api"
# API tải video đa nền tảng (repo ontopcommunity/studiointernet-,
# backend gendownload.com). POST /api/extract {url} -> info + formats.
STUDIOINTERNET_API = "https://superinternetapi.vercel.app/api"

# Telegram Bot API giới hạn file gửi 50MB, để dư 2MB.
MAX_FILE_SIZE = 48 * 1024 * 1024

UA = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
    )
}

SOUNDCLOUD_RE = re.compile(
    r"https?://(?:www\.|m\.)?(?:soundcloud\.com|on\.soundcloud\.com)/\S+",
    re.IGNORECASE,
)
TIKTOK_RE = re.compile(
    r"https?://(?:www\.|m\.|vt\.|vm\.)?tiktok\.com/\S+",
    re.IGNORECASE,
)
URL_RE = re.compile(r"https?://\S+", re.IGNORECASE)

VIDEO_DOMAINS = (
    "youtube.com",
    "youtu.be",
    "instagram.com",
    "facebook.com",
    "fb.watch",
    "twitter.com",
    "x.com",
    "vimeo.com",
    "dailymotion.com",
    "twitch.tv",
    "reddit.com",
    "pinterest.",
    "threads.net",
    "capcut.com",
    "likee.video",
    "snapchat.com",
    "bilibili.com",
)


def _fmt_duration(ms_or_s):
    """Đổi mili-giây (SoundCloud) hoặc giây thành mm:ss."""
    try:
        total = int(ms_or_s)
    except (TypeError, ValueError):
        return ""
    if total > 10000:  # mili-giây
        total //= 1000
    m, s = divmod(total, 60)
    h, m = divmod(m, 60)
    return f"{h}:{m:02d}:{s:02d}" if h else f"{m}:{s:02d}"


def _fmt_num(n):
    """1.234.567 -> 1,2M / 3,4K cho gọn."""
    try:
        n = int(n)
    except (TypeError, ValueError):
        return "0"
    # API TikTok trả heart dạng int32 có dấu -> số lượt thích >2,1 tỷ tràn thành số âm.
    # Đổi sang unsigned 32-bit để ra số đúng (vd: -495029812 -> 3,8 tỷ).
    if n < 0:
        n += 2 ** 32
    if n >= 1_000_000_000:
        return f"{n / 1_000_000_000:.1f}B".replace(".", ",")
    if n >= 1_000_000:
        return f"{n / 1_000_000:.1f}M".replace(".", ",")
    if n >= 1_000:
        return f"{n / 1_000:.1f}K".replace(".", ",")
    return str(n)


def _esc(s):
    return html.escape(str(s or ""), quote=False)


def _open_link_kb(url, label="🔗 Mở link"):
    return InlineKeyboardMarkup(
        [[InlineKeyboardButton(text=label, url=url)]]
    )


def _tmpdir():
    d = Path(tempfile.gettempdir()) / "kaitokid_media"
    d.mkdir(parents=True, exist_ok=True)
    return d


async def _fetch_json(session, url, params=None, timeout=60):
    async with session.get(
        url, params=params, headers=UA, timeout=aiohttp.ClientTimeout(total=timeout)
    ) as resp:
        if resp.status >= 400:
            raise RuntimeError(f"API lỗi {resp.status}")
        return await resp.json(content_type=None)


async def _post_json(session, url, payload, timeout=60):
    async with session.post(
        url, json=payload, headers=UA, timeout=aiohttp.ClientTimeout(total=timeout)
    ) as resp:
        data = await resp.json(content_type=None)
        if resp.status >= 400 or data.get("error"):
            raise RuntimeError(data.get("error") or f"API lỗi {resp.status}")
        return data


async def _download_file(session, url, dest: Path, timeout=300):
    """Tải file trực tiếp về dest, trả về kích thước bytes."""
    async with session.get(
        url, headers=UA, timeout=aiohttp.ClientTimeout(total=timeout)
    ) as resp:
        if resp.status >= 400:
            raise RuntimeError(f"Tải file lỗi {resp.status}")
        size = 0
        with open(dest, "wb") as f:
            async for chunk in resp.content.iter_chunked(512 * 1024):
                f.write(chunk)
                size += len(chunk)
                if size > MAX_FILE_SIZE:
                    raise RuntimeError("File quá lớn (>48MB)")
        return size


def _ytdlp_download(url, outtmpl, audio_only=False):
    """Chạy yt-dlp (blocking) -> trả về (file_path, info)."""
    import yt_dlp

    if audio_only:
        ydl_opts = {
            "format": "bestaudio[ext=m4a]/bestaudio[ext=mp3]/bestaudio/best",
            "outtmpl": outtmpl,
            "quiet": True,
            "no_warnings": True,
            "noplaylist": True,
            "max_filesize": MAX_FILE_SIZE,
            "postprocessors": [],
        }
    else:
        ydl_opts = {
            # File đơn chất lượng cao nhất, không cần ffmpeg để gộp.
            "format": "best[ext=mp4]/best[ext=webm]/best",
            "outtmpl": outtmpl,
            "quiet": True,
            "no_warnings": True,
            "noplaylist": True,
            "max_filesize": MAX_FILE_SIZE,
        }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
        path = ydl.prepare_filename(info)
        # yt-dlp có thể đổi đuôi file thực tế so với prepare_filename
        if not os.path.exists(path):
            base = os.path.splitext(path)[0]
            for cand in Path(outtmpl).parent.glob(os.path.basename(base) + ".*"):
                if cand.is_file() and cand.stat().st_size > 0:
                    path = str(cand)
                    break
        return path, info


# ---------------------------------------------------------------- SoundCloud

async def _handle_soundcloud(msg: Message, url: str):
    status = await msg.reply_text("🎵 Đang lấy nhạc SoundCloud...", quote=True)
    tmp = _tmpdir()
    audio_path = None
    thumb_path = None
    try:
        # API apisynthesis thỉnh thoảng lỗi "No ClientID" (do cào client_id
        # từ soundcloud.com), thử lại tối đa 3 lần.
        data = None
        last_err = None
        for attempt in range(3):
            try:
                async with aiohttp.ClientSession() as session:
                    data = await _fetch_json(
                        session, APISYNTHESIS_BASE, params={"url": url}
                    )
                if data.get("type") == "track" and not data.get("error"):
                    break
                last_err = data.get("error") or "Không phải track"
                data = None
            except Exception as e:
                last_err = str(e)
                data = None
            if attempt < 2:
                await asyncio.sleep(2)

        title = author = permalink = thumb = None
        duration = ""
        duration_sec = 0
        if data:
            title = data.get("title") or "Untitled"
            author = data.get("author") or "Unknown artist"
            duration = _fmt_duration(data.get("duration") or 0)
            duration_sec = int(data.get("duration") or 0) // 1000
            permalink = data.get("permalink_url") or url
            thumb = data.get("thumbnail") or ""

        # Tải nhạc bằng yt-dlp (link HLS của API bị mã hóa, không tải trực tiếp được).
        safe = re.sub(
            r"[^A-Za-z0-9_-]+", "_", f"{author or 'sc'}-{title or 'track'}"
        )[:60]
        outtmpl = str(tmp / f"sc_{safe}.%(ext)s")
        info = None
        try:
            audio_path, info = await asyncio.to_thread(
                _ytdlp_download, url, outtmpl, True
            )
        except Exception as e:
            LOGGER.warning("yt-dlp SoundCloud fail: %s", e)
            audio_path = None

        # Nếu API lỗi mà yt-dlp tải được thì lấy info từ yt-dlp.
        if not data and info:
            title = info.get("title") or "Untitled"
            author = info.get("uploader") or info.get("artist") or "Unknown artist"
            duration = _fmt_duration(info.get("duration") or 0)
            duration_sec = int(info.get("duration") or 0)
            permalink = info.get("webpage_url") or url
            thumb = info.get("thumbnail") or ""
        if not data and not info:
            await status.edit_text(
                "❌ Không lấy được bài này. Kiểm tra lại link SoundCloud nhé."
            )
            return

        # Thumbnail cho file nhạc: Pyrogram cần file local, không nhận URL.
        thumb_path = None
        if thumb:
            try:
                thumb_path = tmp / f"sc_{safe}_thumb.jpg"
                async with aiohttp.ClientSession() as session:
                    await _download_file(session, thumb, thumb_path)
            except Exception:
                thumb_path = None

        caption = (
            "<blockquote>"
            f"🎵 <b>{_esc(title)}</b>\n"
            f"👤 Tác giả: {_esc(author)}\n"
            + (f"⏱ Thời lượng: {duration}\n" if duration else "")
            + "📥 Nguồn: SoundCloud"
            + "</blockquote>"
        )
        kb = _open_link_kb(permalink)

        if audio_path and os.path.exists(audio_path) and os.path.getsize(audio_path) > 0:
            await msg.reply_audio(
                audio=audio_path,
                caption=caption,
                parse_mode=enums.ParseMode.HTML,
                title=title,
                performer=author,
                duration=duration_sec or None,
                thumb=str(thumb_path) if thumb_path else None,
                reply_markup=kb,
                quote=True,
            )
        else:
            # Không tải được file thì vẫn gửi info + nút mở link.
            await msg.reply_text(
                caption + "\n⚠️ Không tải được file nhạc, bấm nút dưới để nghe trên SoundCloud nhé.",
                parse_mode=enums.ParseMode.HTML,
                reply_markup=kb,
                quote=True,
                disable_web_page_preview=False,
            )
        await status.delete()
    except Exception as e:
        LOGGER.exception("SoundCloud handler error")
        try:
            await status.edit_text(f"❌ Lỗi: {e}")
        except Exception:
            pass
    finally:
        if audio_path and os.path.exists(audio_path):
            try:
                os.remove(audio_path)
            except OSError:
                pass
        if thumb_path and os.path.exists(thumb_path):
            try:
                os.remove(thumb_path)
            except OSError:
                pass


# ---------------------------------------------------------------- TikTok

async def _handle_tiktok_video(msg: Message, url: str):
    status = await msg.reply_text("🎬 Đang lấy video TikTok...", quote=True)
    video_path = None
    try:
        async with aiohttp.ClientSession() as session:
            data = await _fetch_json(
                session, f"{TIKTOK_API_BASE}/video", params={"video": url}
            )
        if data.get("error") or data.get("status") != "Live":
            await status.edit_text(
                "❌ Không lấy được video này (có thể bị khóa riêng tư). Kiểm tra lại link nhé."
            )
            return
        author = data.get("author") or {}
        vd = data.get("video_data") or {}
        stats = data.get("stats") or {}
        urls = data.get("urls") or {}
        music = data.get("music") or {}
        dl_url = urls.get("no_watermark")
        if not dl_url:
            await status.edit_text("❌ Không lấy được link tải video.")
            return

        desc = vd.get("description") or ""
        nickname = author.get("nickname") or ""
        unique_id = author.get("uniqueId") or ""
        duration = _fmt_duration(vd.get("duration") or 0)

        tmp = _tmpdir()
        video_path = tmp / f"tt_{vd.get('id') or 'video'}.mp4"
        async with aiohttp.ClientSession() as session:
            await _download_file(session, dl_url, video_path)

        caption = (
            "<blockquote>"
            + (f"🎬 <b>{_esc(desc)}</b>\n" if desc else "🎬 <b>Video TikTok</b>\n")
            + f"👤 {f'@{_esc(unique_id)}' if unique_id else ''}"
            + (f" ({_esc(nickname)})" if nickname else "")
            + "\n"
            + f"❤️ {_fmt_num(stats.get('like'))}  💬 {_fmt_num(stats.get('comment'))}  "
            f"🔁 {_fmt_num(stats.get('share'))}  ▶️ {_fmt_num(stats.get('play'))}\n"
            + (f"⏱ {duration}\n" if duration else "")
            + (f"🎵 Nhạc: {_esc(music.get('title'))}\n" if music.get("title") else "")
            + "📥 Nguồn: TikTok"
            + "</blockquote>"
        )
        await msg.reply_video(
            video=str(video_path),
            caption=caption,
            parse_mode=enums.ParseMode.HTML,
            reply_markup=_open_link_kb(url),
            quote=True,
        )
        await status.delete()
    except Exception as e:
        LOGGER.exception("TikTok video handler error")
        try:
            await status.edit_text(f"❌ Lỗi: {e}")
        except Exception:
            pass
    finally:
        if video_path and os.path.exists(video_path):
            try:
                os.remove(video_path)
            except OSError:
                pass


@app.on_message(filters.command(["tiktok"], COMMAND_HANDLER))
@capture_err
async def tiktok_user_info(_, ctx: Message):
    if len(ctx.command) < 2:
        return await ctx.reply_text(
            "<blockquote>👤 Dùng: <b>/tiktok {username}</b>\nVí dụ: <b>/tiktok charlidamelio</b></blockquote>",
            parse_mode=enums.ParseMode.HTML,
            quote=True,
        )
    username = ctx.command[1].lstrip("@").strip()
    status = await ctx.reply_text("🔍 Đang tìm tài khoản TikTok...", quote=True)
    try:
        async with aiohttp.ClientSession() as session:
            data = await _fetch_json(
                session, TIKTOK_API_BASE, params={"username": username}
            )
        if data.get("status") != "Live" or not data.get("author"):
            return await status.edit_text(
                "❌ Không tìm thấy tài khoản này. Kiểm tra lại username nhé."
            )
        a = data["author"]
        sr = data.get("stats_raw") or {}
        live = data.get("live_info") or {}
        nickname = a.get("nickname") or ""
        unique_id = a.get("uniqueId") or username
        verified = " ✅" if a.get("verified") else ""
        caption = (
            "<blockquote>"
            f"👤 <b>{_esc(nickname)}</b>{verified}\n"
            f"🆔 @{_esc(unique_id)}\n"
            + (f"📝 {_esc(a.get('signature'))}\n" if a.get("signature") else "")
            + f"👥 Follower: <b>{_fmt_num(sr.get('follower'))}</b>"
            f"  •  Đang follow: {_fmt_num(sr.get('following'))}\n"
            + f"❤️ {_fmt_num(sr.get('heart'))}"
            f"  •  🎬 {_fmt_num(sr.get('video'))} video\n"
            + (f"🌍 Khu vực: {_esc(a.get('region'))}\n" if a.get("region") else "")
            + (f"🔴 Đang livestream\n" if live.get("is_live") else "")
            + "📥 Nguồn: TikTok"
            + "</blockquote>"
        )
        kb = _open_link_kb(
            f"https://www.tiktok.com/@{unique_id}", label="🔗 Mở TikTok"
        )
        avatar = a.get("avatar")
        if avatar:
            try:
                await ctx.reply_photo(
                    photo=avatar,
                    caption=caption,
                    parse_mode=enums.ParseMode.HTML,
                    reply_markup=kb,
                    quote=True,
                )
                return await status.delete()
            except Exception:
                pass
        await ctx.reply_text(
            caption,
            parse_mode=enums.ParseMode.HTML,
            reply_markup=kb,
            quote=True,
            disable_web_page_preview=True,
        )
        await status.delete()
    except Exception as e:
        LOGGER.exception("TikTok user handler error")
        try:
            await status.edit_text(f"❌ Lỗi: {e}")
        except Exception:
            pass


# ---------------------------------------------------------------- Video nền tảng khác

def _is_video_domain(url: str):
    try:
        host = urlparse(url).netloc.lower().lstrip("www.")
    except Exception:
        return False
    return any(host == d or host.endswith("." + d) for d in VIDEO_DOMAINS)


def _pick_video_formats(data):
    """Chọn thứ tự thử các format video: ưu tiên 720p, rồi từ cao xuống thấp.

    API trả formats đã xếp từ cao xuống thấp (2160p -> 144p + Audio).
    filesize API trả không đáng tin (thường cùng 1 số) nên phải tải thử
    mới biết có quá 48MB không — thử lần lượt cho tới khi tải được.
    """
    fmts = [f for f in (data.get("formats") or [])
            if f.get("type") == "video" and f.get("url")]
    if not fmts:
        return []
    # Đưa 720p lên đầu (cân bằng chất lượng/dung lượng cho Telegram).
    pref = [f for f in fmts if f.get("label") == "720p"]
    rest = [f for f in fmts if f.get("label") != "720p"]
    return pref + rest


async def _handle_studiointernet(msg: Message, url: str):
    """Tải video đa nền tảng qua API studiointernet (gendownload).

    Nếu API lỗi thì rơi về yt-dlp (_handle_generic_video).
    """
    status = await msg.reply_text("🎬 Đang tải video...", quote=True)
    video_path = None
    try:
        async with aiohttp.ClientSession() as session:
            data = await _post_json(
                session, f"{STUDIOINTERNET_API}/extract", {"url": url}
            )
        candidates = _pick_video_formats(data)
        if not candidates:
            raise RuntimeError("Không có format video.")
        title = data.get("title") or "Video"
        author = data.get("author") or ""
        source = data.get("source") or urlparse(url).netloc
        duration = _fmt_duration(data.get("duration") or 0)
        views = data.get("views")
        likes = data.get("likes")

        tmp = _tmpdir()
        safe = re.sub(r"[^A-Za-z0-9_-]+", "_", urlparse(url).path.strip("/"))[:40]
        video_path = tmp / f"si_{safe or 'video'}.mp4"
        last_err = None
        downloaded = False
        for fmt in candidates:
            try:
                if video_path.exists():
                    video_path.unlink()
                async with aiohttp.ClientSession() as session:
                    await _download_file(session, fmt["url"], video_path)
                downloaded = True
                break
            except Exception as e:
                last_err = e
                LOGGER.warning("studiointernet format %s fail: %s", fmt.get("label"), e)
                continue
        if not downloaded or not video_path.exists() or video_path.stat().st_size == 0:
            raise RuntimeError(str(last_err or "Không tải được video."))

        caption = (
            "<blockquote>"
            f"🎬 <b>{_esc(title)}</b>\n"
            + (f"👤 {_esc(author)}\n" if author else "")
            + (f"⏱ Thời lượng: {duration}\n" if duration else "")
            + (f"👀 {_fmt_num(views)} lượt xem"
               + (f"  •  ❤️ {_fmt_num(likes)}\n" if likes else "\n") if views else "")
            + f"📥 Nguồn: {_esc(source)}"
            + "</blockquote>"
        )
        await msg.reply_video(
            video=str(video_path),
            caption=caption,
            parse_mode=enums.ParseMode.HTML,
            reply_markup=_open_link_kb(url),
            quote=True,
        )
        await status.delete()
    except Exception as e:
        LOGGER.warning("studiointernet fail, fallback yt-dlp: %s", e)
        try:
            await status.delete()
        except Exception:
            pass
        await _handle_generic_video(msg, url)
    finally:
        if video_path and os.path.exists(video_path):
            try:
                os.remove(video_path)
            except OSError:
                pass


async def _handle_generic_video(msg: Message, url: str):
    status = await msg.reply_text("🎬 Đang tải video...", quote=True)
    video_path = None
    try:
        host = urlparse(url).netloc
        safe = re.sub(r"[^A-Za-z0-9_-]+", "_", urlparse(url).path.strip("/"))[:40]
        outtmpl = str(_tmpdir() / f"vid_{safe or 'video'}.%(ext)s")
        video_path, info = await asyncio.to_thread(
            _ytdlp_download, url, outtmpl, False
        )
        if not video_path or not os.path.exists(video_path) or os.path.getsize(video_path) == 0:
            raise RuntimeError("Không tải được video.")
        title = info.get("title") or "Video"
        uploader = info.get("uploader") or info.get("channel") or ""
        duration = _fmt_duration(info.get("duration") or 0)
        caption = (
            "<blockquote>"
            f"🎬 <b>{_esc(title)}</b>\n"
            + (f"👤 { _esc(uploader)}\n" if uploader else "")
            + (f"⏱ Thời lượng: {duration}\n" if duration else "")
            + f"📥 Nguồn: {_esc(host)}"
            + "</blockquote>"
        )
        await msg.reply_video(
            video=video_path,
            caption=caption,
            parse_mode=enums.ParseMode.HTML,
            reply_markup=_open_link_kb(url),
            quote=True,
        )
        await status.delete()
    except Exception as e:
        LOGGER.exception("Generic video handler error")
        err = str(e)
        # YouTube chặn yt-dlp (đòi đăng nhập xác minh không phải bot).
        if ("youtube.com" in url or "youtu.be" in url) and (
            "bot" in err.lower() or "sign in" in err.lower()
        ):
            err_msg = (
                "❌ Không tải được video này (API lỗi, yt-dlp cũng bị YouTube chặn "
                "vì đòi đăng nhập xác minh)."
            )
        else:
            err_msg = (
                "❌ Không tải được video này (có thể link lỗi, video riêng tư hoặc quá lớn)."
            )
        try:
            await status.edit_text(err_msg)
        except Exception:
            pass
    finally:
        if video_path and os.path.exists(video_path):
            try:
                os.remove(video_path)
            except OSError:
                pass


# ---------------------------------------------------------------- Watcher: bắt link trong tin nhắn

@app.on_message(
    filters.text & ~filters.bot & ~filters.via_bot & ~filters.command(COMMAND_HANDLER),
    group=2,
)
@capture_err
async def media_link_watcher(_, msg: Message):
    text = msg.text or ""
    if not text:
        return
    # SoundCloud trước
    m = SOUNDCLOUD_RE.search(text)
    if m:
        return await _handle_soundcloud(msg, m.group(0).rstrip(").,]>"))
    # TikTok
    m = TIKTOK_RE.search(text)
    if m:
        return await _handle_tiktok_video(msg, m.group(0).rstrip(").,]>"))
    # Video nền tảng khác -> API studiointernet, lỗi thì fallback yt-dlp
    for m in URL_RE.finditer(text):
        link = m.group(0).rstrip(").,]>")
        if _is_video_domain(link):
            return await _handle_studiointernet(msg, link)
