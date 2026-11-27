"""Thẻ ảnh thông tin (info card) — vẽ bằng PIL lên ảnh nền riêng từng lệnh.

Bố cục hiện đại, giống ảnh chào mừng (welcomepic trong
kaitokid/plugins/grup_tools.py): tiêu đề ở banner trên, avatar cắt
tròn ở GIỮA, tên + @username, hàng số liệu (icon hiện đại ở trên,
số ở dưới, nhãn ở dưới nữa), bio ở dưới cùng (không chữ "Bio:"),
kèm link nếu bio có link.

Mỗi lệnh có ảnh nền riêng (không dùng chung bg.png):
- /laythongtin  -> assets/bg_info.png   (KaitoKid, nền sáng, chữ đen)
- /tiktok       -> assets/bg_tiktok.png (neon TikTok, nền tối, chữ trắng)

Chữ vẽ bằng cơ chế fallback theo từng ký tự để hiện ĐÚNG Y CHANG như gốc
(không đổi font, không chuẩn hoá), kể cả ký tự đặc biệt:
- MarkaziText-Bold: chữ thường, tiếng Việt có dấu.
- NotoSansMath-Regular: chữ toán học (vd: 𝙈𝙄𝙉𝙃) — chỉ font này vẽ
  được đúng glyph trong Pillow (DejaVu/Liberation/Noto Sans đều ra ô vuông).
- NotoColorEmoji: emoji/icon (🎉 ❤️ 🔥...) vẽ màu, render ở cỡ gốc
  rồi thu nhỏ về cỡ chữ.
Ký tự nào cả 3 cách đều không vẽ được thì mới chuẩn hoá NFKD.
"""

import os
import re
import unicodedata

from PIL import Image, ImageChops, ImageDraw, ImageFont

from kaitokid.core.decorator import asyncify

FONT_PATH = "assets/MarkaziText-Bold.ttf"
FALLBACK_FONT = "assets/DejaVuSans-Bold.ttf"
MATH_FONT = "assets/NotoSansMath-Regular.ttf"
EMOJI_FONT = "assets/NotoColorEmoji.ttf"
DEFAULT_AVATAR = "assets/profilepic.png"

# NotoColorEmoji là font bitmap CBDT, chỉ vẽ được ở cỡ strike gốc.
EMOJI_NATIVE_SIZE = 109

# Regex tìm link (URL) trong bio.
_URL_RE = re.compile(r"https?://\S+|www\.\S+")

# Bố cục từng thẻ (đo từ ảnh nền đã resize về rộng 1024).
STYLES = {
    # bg_info.png 1024x683: banner y~25-90, panel y~140-560, tâm panel x~477.
    "info": {
        "bg": "assets/bg_info.png",
        "canvas": (1024, 683),
        "center_x": 477,
        "title_y": 40, "title_size": 38, "title_fill": "black",
        "avatar_size": 140, "avatar_y": 150,
        "name_size": 30, "name_gap": 12,
        "subtitle_size": 24, "subtitle_gap": 14,
        "stat_icon": 24, "stat_num": 22, "stat_label": 16,
        "stat_gap": 6, "stat_col_w": 160,
        "bio_size": 22, "bio_gap": 10,
        "link_size": 18, "link_gap": 10,
        "footer_size": 20,
        "text_max_w": 700, "fill": "black",
    },
    # bg_tiktok.png 1024x512: banner y~25-85, panel y~110-410, tâm panel x~490.
    "tiktok": {
        "bg": "assets/bg_tiktok.png",
        "canvas": (1024, 512),
        "center_x": 490,
        "title_y": 38, "title_size": 36, "title_fill": "white",
        "avatar_size": 68, "avatar_y": 118,
        "name_size": 24, "name_gap": 8,
        "subtitle_size": 20, "subtitle_gap": 4,
        "stat_icon": 22, "stat_num": 20, "stat_label": 15,
        "stat_gap": 2, "stat_col_w": 140,
        "bio_size": 18, "bio_gap": 6,
        "link_size": 16, "link_gap": 6,
        "footer_size": 18,
        "text_max_w": 560, "fill": "white",
    },
}

# Cache font theo (đường dẫn, cỡ) để không load lại mỗi ký tự.
_FONT_CACHE = {}
# Cache ảnh emoji đã render theo (ký tự, cỡ).
_EMOJI_CACHE = {}
# Cache icon đã vẽ theo (tên, cỡ, màu).
_ICON_CACHE = {}


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
    """Ký tự để vẽ: giữ NGUYÊN như gốc (không đổi font, không chuẩn hoá),
    kể cả ký tự đặc biệt. Font fallback ở _char_font lo việc vẽ đúng."""
    return ch


def _char_font(ch, size):
    """Font để vẽ 1 ký tự: (font, is_emoji)."""
    if _is_emoji(ch):
        return None, True
    if _is_math_alnum(ch):
        # Chữ toán học (vd: 𝙈𝙄𝙉𝙃): chỉ NotoSansMath vẽ được đúng glyph
        # trong Pillow (DejaVu/Liberation/Noto Sans đều ra ô vuông).
        return _load_font(MATH_FONT, size), False
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
        tmp = Image.new("RGBA", (EMOJI_NATIVE_SIZE, EMOJI_NATIVE_SIZE), (0, 0, 0, 0))
        d = ImageDraw.Draw(tmp)
        d.text((0, 0), ch, font=font, embedded_color=True)
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
                cx += size * 0.6
            continue
        ch = _display_char(ch)
        font, _ = _char_font(ch, size)
        try:
            draw.text((cx, y), ch, font=font, fill=fill)
            cx += font.getlength(ch)
        except Exception:
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


# ---------------------------------------------------------------------------
# Icon hiện đại (kiểu SVG) vẽ bằng PIL, dùng cho hàng số liệu.
# Mỗi icon vẽ trên nền trong suốt, màu = màu chữ của thẻ.
# ---------------------------------------------------------------------------

def _icon_heart(size, color):
    im = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    s = size
    d.ellipse([s * 0.06, s * 0.06, s * 0.52, s * 0.52], fill=color)
    d.ellipse([s * 0.48, s * 0.06, s * 0.94, s * 0.52], fill=color)
    d.polygon([(s * 0.06, s * 0.30), (s * 0.94, s * 0.30), (s * 0.50, s * 0.94)], fill=color)
    return im


def _icon_user(size, color):
    im = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    s = size
    d.ellipse([s * 0.33, s * 0.06, s * 0.67, s * 0.40], fill=color)
    d.pieslice([s * 0.12, s * 0.44, s * 0.88, s * 1.05], start=180, end=360, fill=color)
    return im


def _icon_users(size, color):
    im = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    s = size
    d.ellipse([s * 0.06, s * 0.18, s * 0.34, s * 0.46], fill=color)
    d.pieslice([s * 0.00, s * 0.50, s * 0.44, s * 1.00], start=180, end=360, fill=color)
    d.ellipse([s * 0.52, s * 0.06, s * 0.86, s * 0.40], fill=color)
    d.pieslice([s * 0.42, s * 0.44, s * 0.98, s * 1.02], start=180, end=360, fill=color)
    return im


def _icon_play(size, color):
    im = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    s = size
    w = max(2, int(s / 12))
    d.rounded_rectangle([s * 0.06, s * 0.20, s * 0.94, s * 0.80], radius=s * 0.12,
                        outline=color, width=w)
    d.polygon([(s * 0.40, s * 0.36), (s * 0.40, s * 0.64), (s * 0.70, s * 0.50)], fill=color)
    return im


def _icon_globe(size, color):
    im = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    s = size
    w = max(2, int(s / 12))
    d.ellipse([s * 0.06, s * 0.06, s * 0.94, s * 0.94], outline=color, width=w)
    d.line([(s * 0.50, s * 0.06), (s * 0.50, s * 0.94)], fill=color, width=max(1, int(s / 16)))
    d.line([(s * 0.06, s * 0.50), (s * 0.94, s * 0.50)], fill=color, width=max(1, int(s / 16)))
    d.arc([s * 0.28, s * 0.06, s * 0.72, s * 0.94], start=270, end=90, fill=color,
          width=max(1, int(s / 16)))
    d.arc([s * 0.28, s * 0.06, s * 0.72, s * 0.94], start=90, end=270, fill=color,
          width=max(1, int(s / 16)))
    return im


def _icon_image(size, color):
    im = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    s = size
    w = max(2, int(s / 12))
    d.rectangle([s * 0.06, s * 0.16, s * 0.94, s * 0.84], outline=color, width=w)
    d.ellipse([s * 0.20, s * 0.28, s * 0.36, s * 0.44], fill=color)
    d.polygon([(s * 0.10, s * 0.84), (s * 0.48, s * 0.44), (s * 0.86, s * 0.84)], fill=color)
    return im


def _icon_hash(size, color):
    im = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    s = size
    w = max(2, int(s / 10))
    d.line([(s * 0.36, s * 0.10), (s * 0.30, s * 0.90)], fill=color, width=w)
    d.line([(s * 0.68, s * 0.10), (s * 0.62, s * 0.90)], fill=color, width=w)
    d.line([(s * 0.10, s * 0.38), (s * 0.90, s * 0.32)], fill=color, width=w)
    d.line([(s * 0.10, s * 0.66), (s * 0.90, s * 0.60)], fill=color, width=w)
    return im


_ICONS = {
    "heart": _icon_heart,
    "user": _icon_user,
    "users": _icon_users,
    "play": _icon_play,
    "globe": _icon_globe,
    "image": _icon_image,
    "hash": _icon_hash,
}


def _get_icon(name, size, color):
    key = (name, size, color)
    im = _ICON_CACHE.get(key)
    if im is None:
        fn = _ICONS.get(name)
        im = fn(size, color) if fn else None
        _ICON_CACHE[key] = im
    return im


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


def _extract_link(text):
    """Tách link đầu tiên trong bio (nếu có). Trả về (bio_sạch, link)."""
    if not text:
        return "", None
    m = _URL_RE.search(text)
    if not m:
        return text, None
    link = m.group(0)
    bio = text[:m.start()].strip() + " " + text[m.end():].strip()
    bio = " ".join(bio.split())
    return bio, link


@asyncify
def make_info_card(avatar_path, title, out_path, style="info",
                   name=None, subtitle=None, stats=None, bio=None,
                   footer=None, lines=None):
    """Vẽ thẻ thông tin, bố cục hiện đại (avatar giữa, hàng số liệu, bio).

    avatar_path: đường dẫn ảnh đại diện (None -> dùng ảnh mặc định).
    title: tiêu đề ở banner trên.
    out_path: đường dẫn file PNG xuất ra. Trả về out_path.
    style: "info" (/laythongtin) hoặc "tiktok" (/tiktok).
    name: tên chính (lớn). subtitle: dòng phụ (vd: @username).
    stats: list (icon, value, label) — icon: heart/user/users/play/
        globe/image/hash; vẽ thành hàng, icon ở trên, số ở dưới, nhãn
        ở dưới nữa.
    bio: tiểu sử (không cần chữ "Bio:"), link trong bio được tách ra
        hiện ở dòng riêng bên dưới.
    footer: dòng nhỏ cuối thẻ (vd: trạng thái xác minh).
    lines: (tương thích cũ) list (text, size) — dùng khi không có
        name/stats/bio, vẽ các dòng nối tiếp nhau.
    """
    st = STYLES.get(style, STYLES["info"])
    canvas_w, canvas_h = st["canvas"]
    center_x = st["center_x"]
    fill = st["fill"]
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

    y = st["avatar_y"] + st["avatar_size"] + st["name_gap"]

    # Tên chính.
    if name:
        name = str(name).replace("\r", " ").replace("\n", " ").strip()
        name = _fit_text_width(name, st["name_size"], st["text_max_w"])
        _draw_centered(bg, draw, name, y, center_x, st["name_size"], fill=fill)
        y += int(st["name_size"] * 1.35)

    # Dòng phụ (vd: @username).
    if subtitle:
        subtitle = str(subtitle).replace("\r", " ").replace("\n", " ").strip()
        subtitle = _fit_text_width(subtitle, st["subtitle_size"], st["text_max_w"])
        _draw_centered(bg, draw, subtitle, y, center_x, st["subtitle_size"], fill=fill)
        y += int(st["subtitle_size"] * 1.35)

    y += st["subtitle_gap"]

    # Hàng số liệu: icon ở trên, số ở dưới, nhãn ở dưới nữa.
    if stats:
        n = len(stats)
        col_w = st["stat_col_w"]
        total_w = col_w * n
        x0 = center_x - total_w / 2
        icon_size = st["stat_icon"]
        for i, (icon, value, label) in enumerate(stats):
            cx = x0 + col_w * i + col_w / 2
            # Icon.
            im = _get_icon(icon, icon_size, fill)
            if im is not None:
                bg.paste(im, (int(cx - icon_size / 2), int(y)), im)
            # Số.
            value = str(value)
            value = _fit_text_width(value, st["stat_num"], col_w)
            _draw_centered(bg, draw, value, y + icon_size + 4, cx,
                           st["stat_num"], fill=fill)
            # Nhãn.
            if label:
                label = _fit_text_width(str(label), st["stat_label"], col_w)
                _draw_centered(bg, draw, label, y + icon_size + 4 + int(st["stat_num"] * 1.3),
                               cx, st["stat_label"], fill=fill)
        y += icon_size + 4 + int(st["stat_num"] * 1.3) + int(st["stat_label"] * 1.3) + st["stat_gap"]

    # Bio (không chữ "Bio:"), link tách ra dòng riêng.
    link = None
    if bio:
        bio = str(bio).replace("\r", " ").replace("\n", " ").strip()
        bio, link = _extract_link(bio)
        if bio:
            bio = _fit_text_width(bio, st["bio_size"], st["text_max_w"])
            _draw_centered(bg, draw, bio, y, center_x, st["bio_size"], fill=fill)
            y += int(st["bio_size"] * 1.35)
    if link:
        link = _fit_text_width(link, st["link_size"], st["text_max_w"])
        _draw_centered(bg, draw, link, y, center_x, st["link_size"], fill=fill)
        y += int(st["link_size"] * 1.35)

    # Dòng cuối (vd: trạng thái xác minh).
    if footer:
        footer = str(footer).replace("\r", " ").replace("\n", " ").strip()
        footer = _fit_text_width(footer, st["footer_size"], st["text_max_w"])
        _draw_centered(bg, draw, footer, y, center_x, st["footer_size"], fill=fill)
        y += int(st["footer_size"] * 1.35)

    # Tương thích cũ: các dòng nối tiếp nhau.
    if lines:
        for line in lines:
            text, size = line[0], line[1]
            fl = line[2] if len(line) > 2 else fill
            if not text:
                continue
            text = str(text).replace("\r", " ").replace("\n", " ").strip()
            if not text:
                continue
            text = _fit_text_width(text, size, st["text_max_w"])
            _draw_centered(bg, draw, text, y, center_x, size, fill=fl)
            y += int(size * 1.35)

    os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)
    bg.save(out_path)
    return out_path
