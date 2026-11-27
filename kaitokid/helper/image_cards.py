"""Thẻ ảnh thông tin (info card) — vẽ bằng PIL lên nền bg.png.

Cùng cơ chế với ảnh chào mừng thành viên mới (welcomepic trong
kaitokid/plugins/grup_tools.py): nền assets/bg.png, avatar cắt tròn,
chữ vẽ bằng font MarkaziText-Bold. Dùng cho /laythongtin (misc_tools)
và /tiktok (media_downloader).
"""

import os

from PIL import Image, ImageChops, ImageDraw, ImageFont

from kaitokid.core.decorator import asyncify

BG_PATH = "assets/bg.png"
FONT_PATH = "assets/MarkaziText-Bold.ttf"
FALLBACK_FONT = "assets/DejaVuSans-Bold.ttf"
DEFAULT_AVATAR = "assets/profilepic.png"

CANVAS_W, CANVAS_H = 1024, 500
# Vị trí theo tỉ lệ resize 1024x500 của bg.png.
TITLE_Y = 48
AVATAR_X, AVATAR_Y, AVATAR_SIZE = 115, 200, 180
TEXT_X = 325
TEXT_START_Y = 165
TEXT_MAX_W = 540


def circle(pfp, size=(215, 215)):
    """Cắt ảnh thành hình tròn (viền mượt, giống welcomepic)."""
    pfp = pfp.resize(size, Image.LANCZOS).convert("RGBA")
    bigsize = (pfp.size[0] * 3, pfp.size[1] * 3)
    mask = Image.new("L", bigsize, 0)
    draw = ImageDraw.Draw(mask)
    draw.ellipse((0, 0) + bigsize, fill=255)
    mask = mask.resize(pfp.size, Image.LANCZOS)
    mask = ImageChops.darker(mask, pfp.split()[-1])
    pfp.putalpha(mask)
    return pfp


def _font(size):
    try:
        return ImageFont.truetype(FONT_PATH, size)
    except (OSError, IOError):
        return ImageFont.truetype(FALLBACK_FONT, size)


def _fit_text(draw, text, font, max_width):
    """Cắt ngắn text cho vừa max_width, thêm '…' nếu bị cắt."""
    if draw.textlength(text, font=font) <= max_width:
        return text
    ell = "…"
    while text and draw.textlength(text + ell, font=font) > max_width:
        text = text[:-1]
    return text + ell if text else ell


def _draw_centered(draw, text, font, y, fill="black"):
    w = draw.textlength(text, font=font)
    draw.text(((CANVAS_W - w) / 2, y), text, font=font, fill=fill)


@asyncify
def make_info_card(avatar_path, title, lines, out_path):
    """Vẽ thẻ thông tin.

    avatar_path: đường dẫn ảnh đại diện (None -> dùng ảnh mặc định).
    title: tiêu đề ở banner trên.
    lines: list (text, font_size) hoặc (text, font_size, fill).
    out_path: đường dẫn file PNG xuất ra. Trả về out_path.
    """
    bg = Image.open(BG_PATH).convert("RGB").resize((CANVAS_W, CANVAS_H), Image.LANCZOS)
    draw = ImageDraw.Draw(bg)

    # Tiêu đề ở banner trên.
    _draw_centered(draw, title, _font(38), TITLE_Y)

    # Avatar tròn bên trái.
    avatar = avatar_path if avatar_path and os.path.exists(avatar_path) else DEFAULT_AVATAR
    try:
        pfp = Image.open(avatar).convert("RGBA")
        pfp = circle(pfp, size=(AVATAR_SIZE, AVATAR_SIZE))
        bg.paste(pfp, (AVATAR_X, AVATAR_Y), pfp)
    except Exception:
        pass

    # Các dòng thông tin bên phải avatar.
    y = TEXT_START_Y
    for line in lines:
        text, size = line[0], line[1]
        fill = line[2] if len(line) > 2 else "black"
        if not text:
            continue
        font = _font(size)
        text = _fit_text(draw, str(text), font, TEXT_MAX_W)
        draw.text((TEXT_X, y), text, font=font, fill=fill)
        y += int(size * 1.45)

    os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)
    bg.save(out_path)
    return out_path
