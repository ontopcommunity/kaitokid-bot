"""Thẻ ảnh thông tin (info card) — vẽ bằng PIL lên ảnh nền riêng từng lệnh.

Bố cục giống ảnh chào mừng thành viên mới (welcomepic trong
kaitokid/plugins/grup_tools.py): tiêu đề ở banner trên, avatar cắt
tròn ở GIỮA, các dòng thông tin ở DƯỚI avatar (căn giữa).

Mỗi lệnh có ảnh nền riêng (không dùng chung bg.png):
- /laythongtin  -> assets/bg_info.png   (KaitoKid, nền sáng, chữ đen)
- /tiktok       -> assets/bg_tiktok.png (neon TikTok, nền tối, chữ trắng)

Chữ vẽ bằng cơ chế fallback theo từng ký tự để hiện ĐÚNG (không ô vuông):
- MarkaziText-Bold: chữ thường, tiếng Việt có dấu.
- NotoColorEmoji: emoji/icon (🎉 ❤️ 🔥...) vẽ màu, render ở cỡ gốc
  rồi thu nhỏ về cỡ chữ.
- Chữ toán học (vd: 𝙈𝙄𝙉𝙃): Pillow không vẽ được glyph này dù font
  có trong cmap (đã thử DejaVu/Liberation/Noto đều ra ô vuông), nên
  chuẩn hoá NFKD về chữ thường (𝙈 -> M) để hiện đúng.
Ký tự nào cả 3 cách đều không vẽ được thì mới chuẩn hoá NFKD.
"""

import os
import unicodedata

from PIL import Image, ImageChops, ImageDraw, ImageFont

from kaitokid.core.decorator import asyncify

FONT_PATH = "assets/MarkaziText-Bold.ttf"
FALLBACK_FONT = "assets/DejaVuSans-Bold.ttf"
EMOJI_FONT = "assets/NotoColorEmoji.ttf"
DEFAULT_AVATAR = "assets/profilepic.png"

# NotoColorEmoji là font bitmap CBDT, chỉ vẽ được ở cỡ strike gốc.
EMOJI_NATIVE_SIZE = 109

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

# Cache font theo (đường dẫn, cỡ) để không load lại mỗi ký tự.
_FONT_CACHE = {}
# Cache ảnh emoji đã render theo (ký tự, cỡ).
_EMOJI_CACHE = {}


def _load_font(path, size):
    key = (path, size)
    font = _FONT_CACHE.get(key)
    if font is None:
        try:
            font = ImageFont.truetype(path, size)
        except (OSError, IOError):
            font = ImageFont.truetype(FALLBACK_FONT, size)
        _FONT_CACHE[key] = font
    return font


def _font(size):
    return _load_font(FONT_PATH, size)


def _is_emoji(ch):
    """True nếu ký tự là emoji/icon (cần vẽ bằng font emoji màu)."""
    cp = ord(ch)
    if cp in (0xFE0F, 0x200D):  # variation selector, ZWJ: bỏ qua
        return False
    return (
        0x1F000 <= cp <= 0x1FAFF
        or 0x2600 <= cp <= 0x27BF
        or 0x2B00 <= cp <= 0x2BFF
        or 0x2300 <= cp <= 0x23FF
        or cp in (0x00A9, 0x00AE, 0x203C, 0x2049, 0x2122, 0x2139)
    )


def _is_math_alnum(ch):
    """True nếu ký tự là chữ toán học (U+1D400–U+1D7FF, vd: 𝙈𝙄𝙉𝙃)."""
    cp = ord(ch)
    return 0x1D400 <= cp <= 0x1D7FF


def _display_char(ch):
    """Ký tự để vẽ: chữ toán học (Pillow không vẽ được glyph này dù font
    có trong cmap) thì chuẩn hoá NFKD về chữ thường (𝙈 -> M); còn lại
    giữ nguyên để vẽ đúng font gốc (kể cả emoji)."""
    if _is_math_alnum(ch):
        norm = unicodedata.normalize("NFKD", ch)
        return norm if norm else ch
    return ch


def _char_font(ch, size):
    """Font để vẽ 1 ký tự: (font, is_emoji)."""
    if _is_emoji(ch):
        return None, True
    return _font(size), False


def _normalize_fallback(text):
    """Chuẩn hoá NFKD+NFC, chỉ dùng cho ký tự không font nào vẽ được."""
    return unicodedata.normalize("NFC", unicodedata.normalize("NFKD", text))


def _render_emoji(ch, size):
    """Render 1 emoji thành ảnh RGBA cỡ `size` (vẽ ở cỡ gốc rồi thu nhỏ)."""
    key = (ch, size)
    im = _EMOJI_CACHE.get(key)
    if im is not None:
        return im
    try:
        font = ImageFont.truetype(EMOJI_FONT, EMOJI_NATIVE_SIZE)
        # Vẽ lên canvas trong suốt ở cỡ gốc.
        tmp = Image.new("RGBA", (EMOJI_NATIVE_SIZE, EMOJI_NATIVE_SIZE), (0, 0, 0, 0))
        d = ImageDraw.Draw(tmp)
        d.text((0, 0), ch, font=font, embedded_color=True)
        # Cắt phần có nội dung rồi resize về cỡ chữ.
        bbox = tmp.getbbox()
        if bbox:
            tmp = tmp.crop(bbox)
        if tmp.size[0] != size or tmp.size[1] != size:
            tmp = tmp.resize((size, size), Image.LANCZOS)
        im = tmp
    except Exception:
        im = None
    _EMOJI_CACHE[key] = im
    return im


def _char_width(ch, size):
    """Độ rộng 1 ký tự ở cỡ `size` (emoji tính bằng cỡ chữ)."""
    if _is_emoji(ch):
        return size
    ch = _display_char(ch)
    font, _ = _char_font(ch, size)
    try:
        return font.getlength(ch)
    except Exception:
        return size * 0.6


def _text_width(text, size):
    """Tổng độ rộng 1 dòng text (đã gom xuống dòng thành 1 dòng)."""
    w = 0
    for ch in text:
        if ord(ch) in (0xFE0F, 0x200D):
            continue
        w += _char_width(ch, size)
    return w


def _fit_text_width(text, size, max_width):
    """Cắt ngắn text cho vừa max_width, thêm '…' nếu bị cắt."""
    if _text_width(text, size) <= max_width:
        return text
    ell = "…"
    while text and _text_width(text + ell, size) > max_width:
        text = text[:-1]
    return text + ell if text else ell


def _draw_text(bg, draw, text, x, y, size, fill="black"):
    """Vẽ 1 dòng text từ vị trí x, y, fallback font theo từng ký tự.
    Emoji được paste dưới dạng ảnh màu. Trả về độ rộng đã vẽ."""
    cx = x
    for ch in text:
        if ord(ch) in (0xFE0F, 0x200D):
            continue
        if _is_emoji(ch):
            im = _render_emoji(ch, size)
            if im is not None:
                bg.paste(im, (int(cx), int(y)), im)
                cx += size
            else:
                # Không vẽ được emoji thì bỏ qua (không hiện ô vuông).
                cx += size * 0.6
            continue
        ch = _display_char(ch)
        font, _ = _char_font(ch, size)
        try:
            draw.text((cx, y), ch, font=font, fill=fill)
            cx += font.getlength(ch)
        except Exception:
            # Ký tự không vẽ được: chuẩn hoá NFKD rồi vẽ lại.
            norm = _normalize_fallback(ch)
            if norm and norm != ch:
                try:
                    draw.text((cx, y), norm, font=font, fill=fill)
                    cx += font.getlength(norm)
                except Exception:
                    cx += size * 0.6
            else:
                cx += size * 0.6
    return cx - x


def _draw_centered(bg, draw, text, y, center_x, size, fill="black"):
    w = _text_width(text, size)
    _draw_text(bg, draw, text, center_x - w / 2, y, size, fill=fill)


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
    title = str(title).replace("\r", " ").replace("\n", " ").strip()
    title = _fit_text_width(title, st["title_size"], st["text_max_w"])
    _draw_centered(bg, draw, title, st["title_y"], center_x,
                   st["title_size"], fill=st["title_fill"])

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
        # Bio/tên có thể chứa xuống dòng — gộp thành 1 dòng.
        text = str(text).replace("\r", " ").replace("\n", " ").strip()
        if not text:
            continue
        text = _fit_text_width(text, size, st["text_max_w"])
        _draw_centered(bg, draw, text, y, center_x, size, fill=fill)
        y += int(size * 1.35)

    os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)
    bg.save(out_path)
    return out_path
