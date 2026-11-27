"""Thẻ ảnh thông tin (info card) — vẽ bằng PIL lên ảnh nền riêng từng lệnh.

Bố cục giống ảnh chào mừng thành viên mới (welcomepic trong
kaitokid/plugins/grup_tools.py): tiêu đề ở banner trên, avatar cắt
tròn ở GIỮA, các dòng thông tin ở DƯỚI avatar (căn giữa).

Mỗi lệnh có ảnh nền riêng (không dùng chung bg.png):
- /laythongtin  -> assets/bg_info.png   (KaitoKid, nền sáng, chữ đen)
- /tiktok       -> assets/bg_tiktok.png (neon TikTok, nền tối, chữ trắng)
"""

import os

from PIL import Image, ImageChops, ImageDraw, ImageFont

from kaitokid.core.decorator import asyncify

FONT_PATH = "assets/MarkaziText-Bold.ttf"
FALLBACK_FONT = "assets/DejaVuSans-Bold.ttf"
DEFAULT_AVATAR = "assets/profilepic.png"

# Bố cục từng thẻ (đo từ ảnh nền đã resize về rộng 1024).
STYLES = {
    # bg_info.png 1024x683: banner y~25-90, panel y~140-560, tâm panel x~477.
    "info": {
        "bg": "assets/bg_info.png",
        "canvas": (1024, 683),
        "center_x": 477,
        "title_y": 40, "title_size": 38, "title_fill": "black",
        "avatar_size": 200, "avatar_y": 160,
        "text_start_y": 375, "text_max_w": 700, "fill": "black",
    },
    # bg_tiktok.png 1024x512: banner y~25-85, panel y~110-410, tâm panel x~490.
    "tiktok": {
        "bg": "assets/bg_tiktok.png",
        "canvas": (1024, 512),
        "center_x": 490,
        "title_y": 38, "title_size": 36, "title_fill": "white",
        "avatar_size": 130, "avatar_y": 120,
        "text_start_y": 260, "text_max_w": 650, "fill": "white",
    },
}


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


def _draw_centered(draw, text, font, y, center_x, fill="black"):
    w = draw.textlength(text, font=font)
    draw.text((center_x - w / 2, y), text, font=font, fill=fill)


@asyncify
def make_info_card(avatar_path, title, lines, out_path, style="info"):
    """Vẽ thẻ thông tin theo bố cục chào mừng (avatar giữa, text dưới).

    avatar_path: đường dẫn ảnh đại diện (None -> dùng ảnh mặc định).
    title: tiêu đề ở banner trên.
    lines: list (text, font_size) hoặc (text, font_size, fill).
    out_path: đường dẫn file PNG xuất ra. Trả về out_path.
    style: "info" (/laythongtin) hoặc "tiktok" (/tiktok).
    """
    st = STYLES.get(style, STYLES["info"])
    canvas_w, canvas_h = st["canvas"]
    center_x = st["center_x"]
    bg = Image.open(st["bg"]).convert("RGB").resize((canvas_w, canvas_h), Image.LANCZOS)
    draw = ImageDraw.Draw(bg)

    # Tiêu đề ở banner trên (căn giữa).
    _draw_centered(draw, title, _font(st["title_size"]), st["title_y"],
                   center_x, fill=st["title_fill"])

    # Avatar tròn ở giữa panel.
    avatar = avatar_path if avatar_path and os.path.exists(avatar_path) else DEFAULT_AVATAR
    try:
        pfp = Image.open(avatar).convert("RGBA")
        size = st["avatar_size"]
        pfp = circle(pfp, size=(size, size))
        bg.paste(pfp, (center_x - size // 2, st["avatar_y"]), pfp)
    except Exception:
        pass

    # Các dòng thông tin ở dưới avatar (căn giữa).
    y = st["text_start_y"]
    for line in lines:
        text, size = line[0], line[1]
        fill = line[2] if len(line) > 2 else st["fill"]
        if not text:
            continue
        # Bio/tên có thể chứa xuống dòng (vd: TikTok signature) — PIL
        # textlength/draw.text không đo được text nhiều dòng, gộp thành 1 dòng.
        text = str(text).replace("\r", " ").replace("\n", " ").strip()
        if not text:
            continue
        font = _font(size)
        text = _fit_text(draw, text, font, st["text_max_w"])
        _draw_centered(draw, text, font, y, center_x, fill=fill)
        y += int(size * 1.35)

    os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)
    bg.save(out_path)
    return out_path
