"""Mini game KaitoKid: tài xỉu, bầu cua, nối từ, vòng xoay may mắn.

Lệnh: /tx, /bc, /noitu, /lucky, /trochoi (menu), /bxh, /gift, /sodu.
Số dư lưu ở kk_game_balance (database/game_db.py); người chơi mới
được cấp 500.000, hết tiền thì chơi lại được cấp 500.000.
Từ vựng nối từ lấy từ repo tuvungvn (assets/tuvung.txt, 70.446 từ
2 âm tiết). Không có __MODULE__/__HELP__ riêng — phần hướng dẫn
nằm trong module TròChơi (fungame.py).
"""
import asyncio
import pathlib
import random
import re
import time
import unicodedata
from logging import getLogger

from pyrogram import filters
from pyrogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
)

from database import game_db
from kaitokid import app
from kaitokid.core.decorator import new_task
from kaitokid.helper.functions import get_sender
from kaitokid.vars import COMMAND_HANDLER, SUDO

LOGGER = getLogger("KaitoKid")

# ---------------------------------------------------------------- từ vựng
_WORDS = set()
_BY_FIRST = {}
_BY_FIRST_NORM = {}
_NORM_TO_CANON = {}


def _strip(s: str) -> str:
    """Bỏ dấu tiếng Việt để so khớp khi người chơi gõ không dấu."""
    s = unicodedata.normalize("NFD", s)
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    return s.replace("đ", "d").replace("Đ", "D").lower()


def _load_words():
    global _WORDS, _BY_FIRST, _BY_FIRST_NORM, _NORM_TO_CANON
    path = (
        pathlib.Path(__file__).resolve().parent.parent.parent
        / "assets"
        / "tuvung.txt"
    )
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except Exception as e:
        LOGGER.warning(f"Không đọc được assets/tuvung.txt: {e}")
        lines = []
    if not lines:
        lines = [
            "học sinh", "sinh viên", "viên gạch", "gạch đá", "đá quý",
            "quý khách", "khách hàng", "hàng hóa", "hóa học", "học tập",
        ]
    for w in lines:
        w = " ".join(w.strip().lower().split())
        if len(w.split()) != 2:
            continue
        _WORDS.add(w)
        a, _b = w.split()
        _BY_FIRST.setdefault(a, []).append(w)
        na = _strip(a)
        _BY_FIRST_NORM.setdefault(na, []).append(w)
        _NORM_TO_CANON[_strip(w)] = w
    LOGGER.info(f"MiniGame: nạp {_WORDS and len(_WORDS)} từ vựng nối từ.")


_load_words()

# ---------------------------------------------------------------- state
TX_SESSIONS = {}  # (chat_id, user_id) -> {"choice", "amount", "msg_id"}
BC_SESSIONS = {}  # (chat_id, user_id) -> {"bets", "chip", "msg_id"}
NT_SESSIONS = {}  # (chat_id, user_id) -> {"current", "used", "streak", "ts"}
PENDING_CUSTOM = {}  # (chat_id, user_id) -> {"game", "choice"/"chip"}

BC_SYMBOLS = [
    ("nai", "🦌 Nai"),
    ("bau", "🎃 Bầu"),
    ("ga", "🐔 Gà"),
    ("tom", "🦐 Tôm"),
    ("cua", "🦀 Cua"),
    ("ca", "🐟 Cá"),
]
BC_EMOJI = dict(BC_SYMBOLS)

DICE_FACE = {1: "⚀", 2: "⚁", 3: "⚂", 4: "⚃", 5: "⚄", 6: "⚅"}

MIN_BET = 5000
TX_AMOUNTS = [5000, 50000, 500000]
BC_CHIPS = [5000, 50000, 500000]
OWNER_BAL = 10**15  # Số dư chủ bot (hiển thị 'Vô hạn')


def _is_owner(uid: int) -> bool:
    return uid in SUDO


def _fmt_bal(uid: int, bal: int) -> str:
    """Hiển thị số dư: chủ bot là Vô hạn, người khác là số thường."""
    if _is_owner(uid) or bal >= OWNER_BAL:
        return "Vô hạn"
    return _fmt(bal)


def _fmt(n: int) -> str:
    return f"{int(n):,}".replace(",", ".")


def _parse_amount(text: str, balance: int):
    """'5', '5.000', '5k', '1.5m', '1b', '2t', 'all' -> số tiền, None nếu sai.

    k = nghìn, m = triệu, b/t = tỷ. Có hậu tố thì . hoặc , là dấu thập phân
    (1.5m = 1.500.000); không hậu tố thì . hoặc , là phân tách nghìn (5.000 = 5000).
    """
    t = text.strip().lower()
    if t in ("all", "tatca", "tất cả", "het", "hết"):
        return balance if balance > 0 else None
    m = re.fullmatch(r"([\d.,]+)\s*([kmbt]?)", t)
    if not m:
        return None
    num_txt, suf = m.group(1), m.group(2)
    if suf:
        if num_txt.count(".") + num_txt.count(",") > 1:
            return None
        mult = {"k": 1000, "m": 1000000, "b": 1000000000, "t": 1000000000}[suf]
        n = int(float(num_txt.replace(",", ".")) * mult)
    else:
        n = int(num_txt.replace(".", "").replace(",", ""))
    return n if n > 0 else None


async def _ensure_playable(user_id: int):
    """Hết tiền thì cấp lại 500k để chơi tiếp. Trả về (số dư, vừa_cấp).

    Chủ bot luôn có số dư OWNER_BAL (hiển thị Vô hạn).
    """
    if _is_owner(user_id):
        bal = await game_db.get_balance(user_id)
        if bal < OWNER_BAL:
            bal = await game_db.add_balance(user_id, OWNER_BAL - bal)
        return bal, False
    bal = await game_db.get_balance(user_id)
    if bal <= 0:
        bal = await game_db.add_balance(user_id, game_db.START_BALANCE)
        return bal, True
    return bal, False


def _owner_ok(query: CallbackQuery, stored_id: int) -> bool:
    """Chỉ người chơi mới bấm được nút của ván mình (acc kênh: ai cũng bấm)."""
    if stored_id < 0:
        return True
    return bool(query.from_user and query.from_user.id == stored_id)


def _tx_kb(uid: int, stage: str, choice: str = ""):
    if stage == "choice":
        return InlineKeyboardMarkup([
            [
                InlineKeyboardButton("🔴 Tài", callback_data=f"tx:c:tai:{uid}"),
                InlineKeyboardButton("🔵 Xỉu", callback_data=f"tx:c:xiu:{uid}"),
            ],
            [InlineKeyboardButton("❌ Thoát", callback_data=f"tx:x:{uid}")],
        ])
    if stage == "amount":
        row = [
            InlineKeyboardButton(f"{_fmt(a)}", callback_data=f"tx:a:{a}:{uid}")
            for a in TX_AMOUNTS
        ]
        row.append(InlineKeyboardButton("ALL", callback_data=f"tx:a:all:{uid}"))
        return InlineKeyboardMarkup([
            row,
            [InlineKeyboardButton("✏️ Tùy chỉnh", callback_data=f"tx:cu:{uid}")],
            [InlineKeyboardButton("⬅️ Đổi cửa", callback_data=f"tx:back:{uid}")],
        ])
    # after result
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🔄 Chơi tiếp", callback_data=f"tx:again:{uid}"),
            InlineKeyboardButton("❌ Thoát", callback_data=f"tx:x:{uid}"),
        ],
    ])


def _tx_help_text(uid: int, balance: int, name: str = "") -> str:
    who = f"👤 Người chơi: <b>{name}</b>\n" if name else ""
    return (
        "<blockquote expandable>"
        "🎲 <b>TÀI XỈU</b>\n"
        f"{who}"
        f"💰 Số dư: <b>{_fmt_bal(uid, balance)}</b>"
        "</blockquote>"
    )


def _roll_tx():
    d = [random.randint(1, 6) for _ in range(3)]
    total = sum(d)
    if d[0] == d[1] == d[2]:
        return d, total, "bao"
    return d, total, ("tai" if total >= 11 else "xiu")


async def _play_tx(message: Message, uid: int, name: str, choice: str, amount: int):
    if amount < MIN_BET:
        await message.reply_text(
            f"Cược tối thiểu là <b>{_fmt(MIN_BET)}</b>.",
            quote=True,
        )
        return
    bal, refilled = await _ensure_playable(uid)
    if amount > bal:
        await message.reply_text(
            f"Không đủ số dư! Bạn có {_fmt_bal(uid, bal)}, cược tối đa {_fmt_bal(uid, bal)}.",
            quote=True,
        )
        return
    d, total, result = _roll_tx()
    faces = " ".join(DICE_FACE[x] for x in d)
    old = bal
    if result == "bao":
        new = await game_db.add_balance(uid, -amount)
        outcome = "🌪️ <b>BÃO!</b> Ba con giống nhau, nhà cái ăn cả hai cửa."
        delta_txt = f"-{_fmt(amount)}"
    elif result == choice:
        new = await game_db.add_balance(uid, amount * 3)
        outcome = "🎉 <b>THẮNG!</b>"
        delta_txt = f"+{_fmt(amount * 3)}"
    else:
        new = await game_db.add_balance(uid, -amount)
        outcome = "💔 <b>THUA!</b>"
        delta_txt = f"-{_fmt(amount)}"
    res_name = {"tai": "Tài", "xiu": "Xỉu", "bao": "Bão"}[result]
    choice_name = "Tài" if choice == "tai" else "Xỉu"
    refill_txt = "\n💸 Hết tiền nên bot cấp lại 500.000 để chơi tiếp." if refilled else ""
    who = f"👤 Người chơi: <b>{name}</b>\n" if name else ""
    text = (
        "<blockquote expandable>"
        "🎲 <b>KẾT QUẢ TÀI XỈU</b>\n"
        f"{who}"
        f"{faces}  ({d[0]} - {d[1]} - {d[2]})\n"
        f"Tổng: <b>{total}</b> → <b>{res_name}</b>\n"
        f"Bạn cược: <b>{choice_name} {_fmt(amount)}</b>\n"
        f"{outcome} ({delta_txt})\n"
        f"Số dư cũ: {_fmt_bal(uid, old)}\n"
        f"Số dư mới: <b>{_fmt_bal(uid, new)}</b>{refill_txt}"
        "</blockquote>"
    )
    await message.reply_text(text, reply_markup=_tx_kb(uid, "after"), quote=True)


@app.on_message(filters.command(["tx"], COMMAND_HANDLER))
@new_task
async def tx_cmd(client, message: Message):
    uid, name = get_sender(message)
    if uid is None:
        return
    args = message.text.split()[1:] if message.text else []
    bal, _ = await _ensure_playable(uid)
    if len(args) >= 2:
        choice = args[0].lower()
        if choice not in ("tai", "xiu", "tài", "xỉu"):
            await message.reply_text(
                "Cửa cược phải là <b>tài</b> hoặc <b>xỉu</b>. Ví dụ: <code>/tx tài 100</code>",
                quote=True,
            )
            return
        choice = "tai" if choice in ("tai", "tài") else "xiu"
        amount = _parse_amount(args[1], bal)
        if amount is None:
            await message.reply_text("Số tiền cược không hợp lệ.", quote=True)
            return
        await _play_tx(message, uid, name, choice, amount)
        return
    # /tx không tham số: hiện hướng dẫn + chọn cửa
    await message.reply_text(
        _tx_help_text(uid, bal, name), reply_markup=_tx_kb(uid, "choice"), quote=True
    )


@app.on_callback_query(filters.regex(r"^tx:"))
@new_task
async def tx_callback(client, query: CallbackQuery):
    parts = query.data.split(":")
    action = parts[1]
    uid = int(parts[-1])
    if not _owner_ok(query, uid):
        await query.answer("Đây không phải ván của bạn!", show_alert=True)
        return
    chat_id = query.message.chat.id
    key = (chat_id, uid)
    if action == "x":
        await query.message.delete()
        TX_SESSIONS.pop(key, None)
        return
    if action == "c":
        choice = parts[2]
        TX_SESSIONS[key] = {"choice": choice, "amount": None}
        cname = "Tài" if choice == "tai" else "Xỉu"
        pname = await _resolve_name(client, uid)
        bal, _ = await _ensure_playable(uid)
        await query.edit_message_text(
            f"<blockquote expandable>🎲 <b>TÀI XỈU</b>\n"
            f"👤 Người chơi: <b>{pname}</b>\n"
            f"🎯 Cửa: <b>{cname}</b>\n"
            f"💰 Số dư: <b>{_fmt_bal(uid, bal)}</b></blockquote>",
            reply_markup=_tx_kb(uid, "amount", choice),
        )
        return
    if action == "back":
        bal, _ = await _ensure_playable(uid)
        pname = await _resolve_name(client, uid)
        await query.edit_message_text(
            _tx_help_text(uid, bal, pname), reply_markup=_tx_kb(uid, "choice")
        )
        return
    if action == "a":
        sess = TX_SESSIONS.get(key)
        if not sess or not sess.get("choice"):
            await query.answer("Chọn cửa Tài/Xỉu trước đã!", show_alert=True)
            return
        bal, _ = await _ensure_playable(uid)
        amount = bal if parts[2] == "all" else int(parts[2])
        pname = await _resolve_name(client, uid)
        await query.message.delete()
        await _play_tx(query.message, uid, pname, sess["choice"], amount)
        TX_SESSIONS.pop(key, None)
        return
    if action == "cu":
        sess = TX_SESSIONS.get(key)
        if not sess or not sess.get("choice"):
            await query.answer("Chọn cửa Tài/Xỉu trước đã!", show_alert=True)
            return
        PENDING_CUSTOM[key] = {"game": "tx"}
        await query.edit_message_text(
            "<blockquote expandable>✏️ Nhập số tiền cược muốn đặt "
            "(gõ số, ví dụ <code>5k</code>, <code>1m</code>, <code>1b</code>, <code>all</code>).</blockquote>",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("❌ Hủy", callback_data=f"tx:x:{uid}")]
            ]),
        )
        return
    if action == "again":
        bal, _ = await _ensure_playable(uid)
        pname = await _resolve_name(client, uid)
        await query.edit_message_text(
            _tx_help_text(uid, bal, pname), reply_markup=_tx_kb(uid, "choice")
        )
        return

# ---------------------------------------------------------------- bầu cua
def _bc_kb(uid: int, bets: dict, chip: int):
    rows = []
    for i in range(0, 6, 3):
        row = []
        for key, label in BC_SYMBOLS[i:i + 3]:
            amt = bets.get(key, 0)
            row.append(InlineKeyboardButton(
                f"{label}\n{_fmt(amt)}" if amt else label,
                callback_data=f"bc:s:{key}:{uid}",
            ))
        rows.append(row)
    chips = [
        InlineKeyboardButton(
            f"{'✅ ' if c == chip else ''}{_fmt(c)}",
            callback_data=f"bc:chip:{c}:{uid}",
        )
        for c in BC_CHIPS
    ]
    chips.append(InlineKeyboardButton("ALL", callback_data=f"bc:chip:all:{uid}"))
    rows.append(chips)
    rows.append([
        InlineKeyboardButton("✏️ Tùy chỉnh mức cược", callback_data=f"bc:cu:{uid}"),
    ])
    rows.append([
        InlineKeyboardButton("🎲 Lắc", callback_data=f"bc:roll:{uid}"),
        InlineKeyboardButton("❌ Hủy", callback_data=f"bc:x:{uid}"),
    ])
    return InlineKeyboardMarkup(rows)


def _bc_text(uid: int, bets: dict, chip: int, balance: int, name: str = "") -> str:
    total = sum(bets.values())
    lines = [
        "<blockquote expandable>🦀 <b>BẦU CUA TÔM CÁ</b>",
    ]
    if name:
        lines.append(f"👤 Người chơi: <b>{name}</b>")
    lines += [
        f"🎯 Mức cược: <b>{_fmt(chip)}</b>",
        f"💰 Số dư: <b>{_fmt_bal(uid, balance)}</b>",
        f"Đã đặt: <b>{_fmt(total)}</b>",
    ]
    if bets:
        lines.append("—")
        for key, label in BC_SYMBOLS:
            if bets.get(key):
                lines.append(f"{label}: <b>{_fmt(bets[key])}</b>")
    lines.append("</blockquote>")
    return "\n".join(lines)


@app.on_message(filters.command(["bc"], COMMAND_HANDLER))
@new_task
async def bc_cmd(client, message: Message):
    uid, name = get_sender(message)
    if uid is None:
        return
    bal, _ = await _ensure_playable(uid)
    key = (message.chat.id, uid)
    BC_SESSIONS[key] = {"bets": {}, "chip": BC_CHIPS[0], "msg_id": None, "start_bal": bal, "name": name}
    sent = await message.reply_text(
        _bc_text(uid, {}, BC_CHIPS[0], bal, name),
        reply_markup=_bc_kb(uid, {}, BC_CHIPS[0]),
        quote=True,
    )
    BC_SESSIONS[key]["msg_id"] = sent.id


@app.on_callback_query(filters.regex(r"^bc:"))
@new_task
async def bc_callback(client, query: CallbackQuery):
    parts = query.data.split(":")
    action = parts[1]
    uid = int(parts[-1])
    if not _owner_ok(query, uid):
        await query.answer("Đây không phải ván của bạn!", show_alert=True)
        return
    key = (query.message.chat.id, uid)
    sess = BC_SESSIONS.get(key)
    if action == "x":
        if sess and sess["bets"]:
            refund = sum(sess["bets"].values())
            await game_db.add_balance(uid, refund)
        BC_SESSIONS.pop(key, None)
        await query.message.delete()
        return
    if sess is None:
        await query.answer("Ván này đã hết hạn, gõ /bc để chơi ván mới.", show_alert=True)
        return
    if action == "chip":
        bal, _ = await _ensure_playable(uid)
        sess["chip"] = bal if parts[2] == "all" else int(parts[2])
        await query.edit_message_text(
            _bc_text(uid, sess["bets"], sess["chip"], bal, sess.get("name", "")),
            reply_markup=_bc_kb(uid, sess["bets"], sess["chip"]),
        )
        return
    if action == "cu":
        PENDING_CUSTOM[key] = {"game": "bc"}
        await query.answer("Nhập mức cược mới vào khung chat.", show_alert=True)
        return
    if action == "s":
        symbol = parts[2]
        bal, _ = await _ensure_playable(uid)
        chip = sess["chip"]
        if chip <= 0:
            await query.answer("Chọn mức cược trước đã!", show_alert=True)
            return
        if chip > bal:
            await query.answer(
                f"Không đủ số dư! Bạn còn {_fmt_bal(uid, bal)}.", show_alert=True
            )
            return
        await game_db.add_balance(uid, -chip)
        sess["bets"][symbol] = sess["bets"].get(symbol, 0) + chip
        bal -= chip
        await query.edit_message_text(
            _bc_text(uid, sess["bets"], sess["chip"], bal, sess.get("name", "")),
            reply_markup=_bc_kb(uid, sess["bets"], sess["chip"]),
        )
        return
    if action == "roll":
        if not sess["bets"]:
            await query.answer("Đặt cược vào ít nhất một ô trước đã!", show_alert=True)
            return
        dice = [random.choice([k for k, _ in BC_SYMBOLS]) for _ in range(3)]
        counts = {k: dice.count(k) for k, _ in BC_SYMBOLS}
        total_bet = sum(sess["bets"].values())
        total_back = 0
        detail = []
        for key, label in BC_SYMBOLS:
            b = sess["bets"].get(key, 0)
            if not b:
                continue
            c = counts[key]
            if c:
                back = b * (c + 1)
                total_back += back
                detail.append(f"{label}: ra {c} lần → +{_fmt(back - b)}")
            else:
                detail.append(f"{label}: không ra → -{_fmt(b)}")
        old = sess.get("start_bal", await game_db.get_balance(uid))
        new = await game_db.add_balance(uid, total_back)
        net = total_back - total_bet
        faces = " ".join(BC_EMOJI[k] for k in dice)
        verdict = "🎉 <b>THẮNG!</b>" if net > 0 else ("😐 <b>HÒA!</b>" if net == 0 else "💔 <b>THUA!</b>")
        pname = sess.get("name", "")
        who = f"👤 Người chơi: <b>{pname}</b>\n" if pname else ""
        text = (
            "<blockquote expandable>🦀 <b>KẾT QUẢ BẦU CUA</b>\n"
            f"{who}"
            f"{faces}\n"
            + "\n".join(detail)
            + f"\n{verdict} ({'+' if net >= 0 else ''}{_fmt(net)})\n"
            f"Tổng cược: {_fmt(total_bet)}  •  Nhận lại: {_fmt(total_back)}\n"
            f"Số dư cũ: {_fmt_bal(uid, old)}\n"
            f"Số dư mới: <b>{_fmt_bal(uid, new)}</b>"
            "</blockquote>"
        )
        BC_SESSIONS.pop(key, None)
        await query.edit_message_text(
            text,
            reply_markup=InlineKeyboardMarkup([
                [
                    InlineKeyboardButton("🔄 Chơi tiếp", callback_data=f"mg:bc:{uid}"),
                    InlineKeyboardButton("❌ Thoát", callback_data=f"bc:x:{uid}"),
                ],
            ]),
        )
        return

# ---------------------------------------------------------------- nối từ
NT_TIMEOUT = 300  # 5 phút không chơi thì ván tự hết


def _canon_word(raw: str):
    """Chuẩn hóa từ người chơi về dạng có dấu trong list, None nếu không có."""
    w = " ".join(raw.strip().lower().split())
    if len(w.split()) != 2:
        return None
    if w in _WORDS:
        return w
    return _NORM_TO_CANON.get(_strip(w))


def _bot_pick(last_syllable: str, used: set):
    cands = _BY_FIRST.get(last_syllable) or _BY_FIRST_NORM.get(_strip(last_syllable), [])
    cands = [w for w in cands if w not in used]
    return random.choice(cands) if cands else None


@app.on_message(filters.command(["noitu"], COMMAND_HANDLER))
@new_task
async def noitu_cmd(client, message: Message):
    uid, name = get_sender(message)
    if uid is None:
        return
    args = message.text.split()[1:] if message.text else []
    key = (message.chat.id, uid)
    # /noitu dung: dừng ván đang chơi
    if args and args[0].lower() in ("dung", "stop"):
        sess = NT_SESSIONS.pop(key, None)
        if sess:
            bal = await game_db.get_balance(uid)
            await message.reply_text(
                f"🔤 Dừng nối từ. Chuỗi đúng liên tiếp: <b>{sess['streak']}</b>. "
                f"Số dư: <b>{_fmt_bal(uid, bal)}</b>.",
                quote=True,
            )
        else:
            await message.reply_text("Bạn không có ván nối từ nào đang chơi.", quote=True)
        return
    bal, _ = await _ensure_playable(uid)
    key = (message.chat.id, uid)
    start = random.choice(list(_WORDS))
    NT_SESSIONS[key] = {
        "current": start,
        "used": {start},
        "streak": 0,
        "ts": time.time(),
        "name": name,
    }
    await message.reply_text(
        "<blockquote expandable>🔤 <b>NỐI TỪ</b>\n"
        f"👤 Người chơi: <b>{name}</b>\n"
        f"💰 Số dư: <b>{_fmt_bal(uid, bal)}</b>\n"
        f"Bot ra từ: <b>{start}</b>"
        "</blockquote>",
        quote=True,
    )


async def _noitu_play(client, message: Message, uid: int, raw: str):
    key = (message.chat.id, uid)
    sess = NT_SESSIONS.get(key)
    if not sess:
        return False
    if time.time() - sess["ts"] > NT_TIMEOUT:
        NT_SESSIONS.pop(key, None)
        await message.reply_text(
            "🔤 Ván nối từ đã hết hạn (5 phút không chơi). Gõ /noitu để chơi lại.",
            quote=True,
        )
        return True
    sess["ts"] = time.time()
    word = _canon_word(raw)
    cur = sess["current"]
    last = cur.split()[1]
    if word is None:
        NT_SESSIONS.pop(key, None)
        await message.reply_text(
            "<blockquote expandable>🔤 <b>THUA!</b>\n"
            f"👤 Người chơi: <b>{sess.get('name', '')}</b>\n"
            f"Từ <b>{raw.strip()}</b> không có trong từ điển.\n"
            f"Chuỗi đúng liên tiếp: <b>{sess['streak']}</b>. Gõ /noitu để chơi lại."
            "</blockquote>",
            quote=True,
        )
        return True
    if word in sess["used"]:
        NT_SESSIONS.pop(key, None)
        await message.reply_text(
            "<blockquote expandable>🔤 <b>THUA!</b>\n"
            f"👤 Người chơi: <b>{sess.get('name', '')}</b>\n"
            f"Từ <b>{word}</b> đã dùng rồi.\n"
            f"Chuỗi đúng liên tiếp: <b>{sess['streak']}</b>. Gõ /noitu để chơi lại."
            "</blockquote>",
            quote=True,
        )
        return True
    if _strip(word.split()[0]) != _strip(last):
        NT_SESSIONS.pop(key, None)
        await message.reply_text(
            "<blockquote expandable>🔤 <b>THUA!</b>\n"
            f"👤 Người chơi: <b>{sess.get('name', '')}</b>\n"
            f"Từ phải bắt đầu bằng âm <b>{last}</b> (âm cuối của <b>{cur}</b>).\n"
            f"Chuỗi đúng liên tiếp: <b>{sess['streak']}</b>. Gõ /noitu để chơi lại."
            "</blockquote>",
            quote=True,
        )
        return True
    # Đúng: thưởng 5% số dư, bot nối tiếp.
    bal = await game_db.get_balance(uid)
    reward = max(10, int(bal * 0.05)) if not _is_owner(uid) else 0
    new = await game_db.add_balance(uid, reward) if reward else bal
    sess["used"].add(word)
    sess["streak"] += 1
    nxt = _bot_pick(word.split()[1], sess["used"])
    if nxt is None:
        NT_SESSIONS.pop(key, None)
        reward_txt = f"Thưởng: +{_fmt(reward)}  •  " if not _is_owner(uid) else ""
        await message.reply_text(
            "<blockquote expandable>🔤 <b>BẠN THẮNG VÁN NÀY!</b>\n"
            f"👤 Người chơi: <b>{sess.get('name', '')}</b>\n"
            f"Từ <b>{word}</b> đúng, bot không còn từ nào để nối tiếp.\n"
            f"{reward_txt}Số dư mới: <b>{_fmt_bal(uid, new)}</b>\n"
            f"Chuỗi đúng liên tiếp: <b>{sess['streak']}</b>. Gõ /noitu để chơi lại."
            "</blockquote>",
            quote=True,
        )
        return True
    sess["current"] = nxt
    sess["used"].add(nxt)
    reward_txt = f"+{_fmt(reward)} (5% số dư)  •  " if not _is_owner(uid) else ""
    await message.reply_text(
        "<blockquote expandable>🔤 <b>ĐÚNG!</b> "
        f"{reward_txt}Số dư: <b>{_fmt_bal(uid, new)}</b>\n"
        f"Bot nối: <b>{nxt}</b> — tới lượt bạn."
        "</blockquote>",
        quote=True,
    )
    return True


# ---------------------------------------------------------------- vòng xoay
LUCKY_SLOTS = [
    ("x100", 1, "💎 x100 SỐ DƯ"),
    ("x10", 3, "🌟 x10 SỐ DƯ"),
    ("x5", 6, "✨ x5 SỐ DƯ"),
    ("x2", 15, "🎈 x2 SỐ DƯ"),
    ("bonus", 5, "🎁 THƯỞNG 1TR – 1TỶ"),
    ("lose50", 10, "📉 MẤT 50% SỐ DƯ"),
    ("lose20", 15, "📉 MẤT 20% SỐ DƯ"),
    ("lose10", 20, "📉 MẤT 10% SỐ DƯ"),
    ("loseall", 2, "💥 MẤT SẠCH"),
    ("nothing", 23, "😶 KHÔNG CÓ GÌ"),
]


def _roll_lucky():
    total = sum(w for _, w, _ in LUCKY_SLOTS)
    r = random.randint(1, total)
    acc = 0
    for key, w, label in LUCKY_SLOTS:
        acc += w
        if r <= acc:
            return key, label
    return "nothing", "😶 KHÔNG CÓ GÌ"


def _roll_bonus():
    r = random.random()
    if r < 0.70:
        return random.randint(1000000, 10000000)
    if r < 0.90:
        return random.randint(10000000, 100000000)
    if r < 0.98:
        return random.randint(100000000, 500000000)
    return random.randint(500000000, 1000000000)


def _lucky_kb(uid: int, spinning: bool = False):
    if spinning:
        return None
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🎡 Quay", callback_data=f"lucky:spin:{uid}")],
        [InlineKeyboardButton("❌ Thoát", callback_data=f"lucky:x:{uid}")],
    ])


def _lucky_menu_text(uid: int, balance: int, name: str = "") -> str:
    lines = [
        "<blockquote expandable>🎡 <b>VÒNG XOAY MAY MẮN</b>",
    ]
    if name:
        lines.append(f"👤 Người chơi: <b>{name}</b>")
    lines += [
        f"💰 Số dư: <b>{_fmt_bal(uid, balance)}</b>",
    ]
    lines.append("</blockquote>")
    return "\n".join(lines)


@app.on_message(filters.command(["lucky"], COMMAND_HANDLER))
@new_task
async def lucky_cmd(client, message: Message):
    uid, name = get_sender(message)
    if uid is None:
        return
    bal, _ = await _ensure_playable(uid)
    await message.reply_text(
        _lucky_menu_text(uid, bal, name), reply_markup=_lucky_kb(uid), quote=True
    )


@app.on_callback_query(filters.regex(r"^lucky:"))
@new_task
async def lucky_callback(client, query: CallbackQuery):
    parts = query.data.split(":")
    action = parts[1]
    uid = int(parts[-1])
    if not _owner_ok(query, uid):
        await query.answer("Đây không phải vòng xoay của bạn!", show_alert=True)
        return
    if action == "x":
        await query.message.delete()
        return
    if action == "spin":
        bal, _ = await _ensure_playable(uid)
        pname = await _resolve_name(client, uid)
        await query.edit_message_text(
            f"<blockquote expandable>🎡 <b>VÒNG XOAY MAY MẮN</b>\n"
            f"👤 Người chơi: <b>{pname}</b>\n"
            "Đang quay...\n"
            "🎡 🎡 🎡</blockquote>",
        )
        await asyncio.sleep(1.2)
        key, label = _roll_lucky()
        old = bal
        if key in ("x2", "x5", "x10", "x100"):
            mult = int(key[1:])
            new = await game_db.add_balance(uid, bal * (mult - 1))
            delta = f"+{_fmt(bal * (mult - 1))}"
        elif key == "bonus":
            amt = _roll_bonus()
            new = await game_db.add_balance(uid, amt)
            delta = f"+{_fmt(amt)}"
        elif key == "lose50":
            new = await game_db.add_balance(uid, -int(bal * 0.5))
            delta = f"-{_fmt(int(bal * 0.5))}"
        elif key == "lose20":
            new = await game_db.add_balance(uid, -int(bal * 0.2))
            delta = f"-{_fmt(int(bal * 0.2))}"
        elif key == "lose10":
            new = await game_db.add_balance(uid, -int(bal * 0.1))
            delta = f"-{_fmt(int(bal * 0.1))}"
        elif key == "loseall":
            new = await game_db.add_balance(uid, -bal)
            delta = f"-{_fmt(bal)}"
        else:
            new = bal
            delta = "0"
        text = (
            "<blockquote expandable>🎡 <b>KẾT QUẢ VÒNG XOAY</b>\n"
            f"👤 Người chơi: <b>{pname}</b>\n"
            f"Ô trúng: <b>{label}</b>\n"
            f"Kết quả: <b>{delta}</b>\n"
            f"Số dư cũ: {_fmt_bal(uid, old)}\n"
            f"Số dư mới: <b>{_fmt_bal(uid, new)}</b>"
            "</blockquote>"
        )
        await query.edit_message_text(
            text,
            reply_markup=InlineKeyboardMarkup([
                [
                    InlineKeyboardButton("🔄 Quay tiếp", callback_data=f"lucky:spin:{uid}"),
                    InlineKeyboardButton("❌ Thoát", callback_data=f"lucky:x:{uid}"),
                ],
            ]),
        )
        return

# ---------------------------------------------------------------- menu / bxh / gift / sodu
def _menu_kb(uid: int):
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🎲 Tài xỉu", callback_data=f"mg:tx:{uid}"),
            InlineKeyboardButton("🦀 Bầu cua", callback_data=f"mg:bc:{uid}"),
        ],
        [
            InlineKeyboardButton("🔤 Nối từ", callback_data=f"mg:noitu:{uid}"),
            InlineKeyboardButton("🎡 Vòng xoay", callback_data=f"mg:lucky:{uid}"),
        ],
        [
            InlineKeyboardButton("💰 Số dư", callback_data=f"mg:sodu:{uid}"),
            InlineKeyboardButton("🏆 Bảng xếp hạng", callback_data=f"mg:bxh:{uid}"),
        ],
    ])


def _menu_text(uid: int, balance: int, name: str = "") -> str:
    who = f"👤 Người chơi: <b>{name}</b>\n" if name else ""
    return (
        "<blockquote expandable>🎮 <b>MENU TRÒ CHƠI</b>\n"
        f"{who}"
        f"💰 Số dư: <b>{_fmt_bal(uid, balance)}</b>"
        "</blockquote>"
    )


@app.on_message(filters.command(["trochoi", "game", "minigame"], COMMAND_HANDLER))
@new_task
async def menu_cmd(client, message: Message):
    uid, name = get_sender(message)
    if uid is None:
        return
    bal, _ = await _ensure_playable(uid)
    await message.reply_text(_menu_text(uid, bal, name), reply_markup=_menu_kb(uid), quote=True)


@app.on_callback_query(filters.regex(r"^mg:"))
@new_task
async def menu_callback(client, query: CallbackQuery):
    parts = query.data.split(":")
    action = parts[1]
    uid = int(parts[-1])
    if not _owner_ok(query, uid):
        await query.answer("Đây không phải menu của bạn!", show_alert=True)
        return
    bal, _ = await _ensure_playable(uid)
    pname = await _resolve_name(client, uid)
    if action == "tx":
        await query.edit_message_text(_tx_help_text(uid, bal, pname), reply_markup=_tx_kb(uid, "choice"))
    elif action == "bc":
        key = (query.message.chat.id, uid)
        BC_SESSIONS[key] = {"bets": {}, "chip": BC_CHIPS[0], "msg_id": query.message.id, "start_bal": bal, "name": pname}
        await query.edit_message_text(
            _bc_text(uid, {}, BC_CHIPS[0], bal, pname),
            reply_markup=_bc_kb(uid, {}, BC_CHIPS[0]),
        )
    elif action == "noitu":
        start = random.choice(list(_WORDS))
        key = (query.message.chat.id, uid)
        NT_SESSIONS[key] = {"current": start, "used": {start}, "streak": 0, "ts": time.time(), "name": pname}
        await query.edit_message_text(
            "<blockquote expandable>🔤 <b>NỐI TỪ</b>\n"
            f"👤 Người chơi: <b>{pname}</b>\n"
            f"💰 Số dư: <b>{_fmt_bal(uid, bal)}</b>\n"
            f"Bot ra từ: <b>{start}</b></blockquote>"
        )
    elif action == "lucky":
        await query.edit_message_text(_lucky_menu_text(uid, bal, pname), reply_markup=_lucky_kb(uid))
    elif action == "sodu":
        rank = await game_db.get_rank(uid)
        await query.edit_message_text(
            "<blockquote expandable>💰 <b>SỐ DƯ</b>\n"
            f"👤 Người chơi: <b>{pname}</b>\n"
            f"Số dư: <b>{_fmt_bal(uid, bal)}</b>\n"
            f"Hạng: <b>#{rank}</b> toàn bot</blockquote>",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("⬅️ Menu", callback_data=f"mg:back:{uid}")]
            ]),
        )
    elif action == "bxh":
        await query.edit_message_text(
            await _bxh_text(client, uid),
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("⬅️ Menu", callback_data=f"mg:back:{uid}")]
            ]),
        )
    elif action == "back":
        await query.edit_message_text(_menu_text(uid, bal, pname), reply_markup=_menu_kb(uid))


_NAME_CACHE = {}


async def _resolve_name(client, user_id: int) -> str:
    if user_id in _NAME_CACHE:
        return _NAME_CACHE[user_id]
    name = None
    try:
        u = await client.get_users(user_id)
        name = u.first_name or u.username or str(user_id)
    except Exception:
        try:
            c = await client.get_chat(user_id)
            name = c.title or str(user_id)
        except Exception:
            name = str(user_id)
    _NAME_CACHE[user_id] = name
    return name


async def _bxh_text(client, uid: int) -> str:
    top = await game_db.top_balances(10)
    lines = ["<blockquote expandable>🏆 <b>BẢNG XẾP HẠNG SỐ TIỀN</b>"]
    if not top:
        lines.append("Chưa có ai chơi.")
    for i, row in enumerate(top, 1):
        name = await _resolve_name(client, row["user_id"])
        medal = {1: "🥇", 2: "🥈", 3: "🥉"}.get(i, f"{i}.")
        mark = " 👈 bạn" if row["user_id"] == uid else ""
        lines.append(f"{medal} {name} — <b>{_fmt_bal(row['user_id'], row['balance'])}</b>{mark}")
    rank = await game_db.get_rank(uid)
    bal = await game_db.get_balance(uid)
    if rank and rank > 10:
        lines.append(f"—\nHạng của bạn: <b>#{rank}</b> — {_fmt_bal(uid, bal)}")
    lines.append("</blockquote>")
    return "\n".join(lines)


@app.on_message(filters.command(["bxh", "bangxephang"], COMMAND_HANDLER))
@new_task
async def bxh_cmd(client, message: Message):
    uid, name = get_sender(message)
    if uid is None:
        return
    await message.reply_text(await _bxh_text(client, uid), quote=True)


@app.on_message(filters.command(["sodu", "balance"], COMMAND_HANDLER))
@new_task
async def sodu_cmd(client, message: Message):
    uid, name = get_sender(message)
    if uid is None:
        return
    bal, refilled = await _ensure_playable(uid)
    rank = await game_db.get_rank(uid)
    extra = "\n💸 Hết tiền nên bot cấp lại 500.000." if refilled else ""
    await message.reply_text(
        f"<blockquote expandable>💰 <b>SỐ DƯ</b>\n"
        f"👤 Người chơi: <b>{name}</b>\n"
        f"Số dư: <b>{_fmt_bal(uid, bal)}</b>\n"
        f"Hạng: <b>#{rank}</b> toàn bot{extra}</blockquote>",
        quote=True,
    )


@app.on_message(filters.command(["gift"], COMMAND_HANDLER))
@new_task
async def gift_cmd(client, message: Message):
    uid, name = get_sender(message)
    if uid is None:
        return
    args = message.text.split()[1:] if message.text else []
    target_id = None
    amount_txt = None
    # /gift <amount> khi reply tin người khác
    if message.reply_to_message and len(args) == 1:
        r = message.reply_to_message
        target_id = r.from_user.id if r.from_user else (
            r.sender_chat.id if getattr(r, "sender_chat", None) else None
        )
        amount_txt = args[0]
    elif len(args) >= 2:
        raw = args[0].lstrip("@")
        if raw.lstrip("-").isdigit():
            target_id = int(raw)
        else:
            try:
                u = await client.get_users(raw)
                target_id = u.id
            except Exception:
                await message.reply_text(
                    f"Không tìm thấy người chơi @{raw}.", quote=True
                )
                return
        amount_txt = args[1]
    else:
        await message.reply_text(
            "Dùng: <code>/gift @username số_tiền</code> hoặc "
            "<code>/gift 123456789 số_tiền</code> (reply tin người nhận + "
            "<code>/gift số_tiền</code> cũng được).",
            quote=True,
        )
        return
    if target_id is None:
        await message.reply_text("Không xác định được người nhận.", quote=True)
        return
    bal = await game_db.get_balance(uid)
    amount = _parse_amount(amount_txt, bal)
    if amount is None:
        await message.reply_text("Số tiền tặng không hợp lệ.", quote=True)
        return
    ok, reason, sender_new, receiver_new = await game_db.transfer(uid, target_id, amount)
    if not ok:
        await message.reply_text(f"❌ {reason} Số dư của bạn: {_fmt_bal(uid, bal)}.", quote=True)
        return
    recv_name = await _resolve_name(client, target_id)
    await message.reply_text(
        "<blockquote expandable>🎁 <b>TẶNG TIỀN THÀNH CÔNG</b>\n"
        f"Người nhận: <b>{recv_name}</b>\n"
        f"Số tiền: <b>{_fmt(amount)}</b>\n"
        f"Số dư của bạn còn: <b>{_fmt_bal(uid, sender_new)}</b>\n"
        f"Số dư người nhận: <b>{_fmt_bal(target_id, receiver_new)}</b>"
        "</blockquote>",
        quote=True,
    )


# ---------------------------------------------------------------- watcher: nhập tiền tùy chỉnh + nối từ
@app.on_message(filters.text & ~filters.regex(r"^[!/.]"), group=3)
@new_task
async def game_input_watcher(client, message: Message):
    uid, name = get_sender(message)
    if uid is None or not message.text:
        return
    key = (message.chat.id, uid)
    # 1) Nhập số tiền tùy chỉnh (tài xỉu / bầu cua)
    pend = PENDING_CUSTOM.get(key)
    if pend:
        PENDING_CUSTOM.pop(key, None)
        bal, _ = await _ensure_playable(uid)
        amount = _parse_amount(message.text, bal)
        if amount is None:
            await message.reply_text("Số tiền không hợp lệ, ván đã hủy.", quote=True)
            return
        if amount < MIN_BET:
            await message.reply_text(
                f"Cược tối thiểu là <b>{_fmt(MIN_BET)}</b>.",
                quote=True,
            )
            return
        if pend["game"] == "tx":
            sess = TX_SESSIONS.get(key)
            if not sess or not sess.get("choice"):
                await message.reply_text("Ván tài xỉu đã hết hạn, gõ /tx để chơi lại.", quote=True)
                return
            TX_SESSIONS.pop(key, None)
            await _play_tx(message, uid, name, sess["choice"], amount)
        else:
            sess = BC_SESSIONS.get(key)
            if not sess:
                await message.reply_text("Ván bầu cua đã hết hạn, gõ /bc để chơi lại.", quote=True)
                return
            sess["chip"] = amount
            await message.reply_text(
                f"✏️ Mức cược đã đặt thành <b>{_fmt(amount)}</b>. "
                "Bấm vào các ô để đặt cược.",
                quote=True,
            )
        return
    # 2) Nối từ
    if key in NT_SESSIONS:
        await _noitu_play(client, message, uid, message.text)
