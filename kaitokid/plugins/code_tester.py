import aiohttp
import logging
from logging import getLogger
from pyrogram import enums, filters
from pyrogram.errors import MessageTooLong

from kaitokid import app
from kaitokid.helper.tools import rentry
from kaitokid.vars import COMMAND_HANDLER

LOGGER = getLogger("KaitoKid")

__MODULE__ = "ThửCode"
__HELP__ = """
Tính năng này cho phép bạn chạy nhiều ngôn ngữ lập trình thông qua bot này thông qua api Glot.io. Sau đây là danh sách các ngôn ngữ được hỗ trợ, chạy bằng / , . hoặc ! như ví dụ bên dưới.

<blockquote>Danh sách các ngôn ngữ lập trình được hỗ trợ:
~> assembly
~> ats
~> bash
~> c
~> clojure
~> cobol
~> coffeescript
~> cpp
~> crystal
~> csharp
~> d
~> elixir
~> elm
~> erlang
~> fsharp
~> go
~> groovy
~> haskell
~> idris
~> java
~> javascript
~> julia
~> kotlin
~> lua
~> mercury
~> nim
~> nix
~> ocaml
~> perl
~> php
~> python
~> raku
~> ruby
~> rust
~> scala
~> swift
~> typescript

**Ví dụ:**
~> `!python print("Xin chào, tôi là KaitoKid")`</blockquote>
"""


async def listcode():
    async with aiohttp.ClientSession() as session:
        r = await session.get("https://glot.io/api/run")
        return await r.json()


async def glot(lang, langcode, code):
    async with aiohttp.ClientSession() as session:
        data = {"files": [{"name": f"kaitokid.{langcode}", "content": code}]}
        headers = {
            "content-type": "application/json",
            "Authorization": "Token b8a2b75a-a078-4089-869c-e53d448b1ebb",
        }
        r = await session.post(
            f"https://glot.io/api/run/{lang}/latest", headers=headers, json=data
        )
        return await r.json()


@app.on_message(filters.command(["codelist"], COMMAND_HANDLER))
async def list_lang(_, message):
    daftarlang = await listcode()
    list_ = "".join(f"~> {i['name']}\n" for i in daftarlang)
    return await message.reply(
        f"<b>Danh sách ngôn ngữ lập trình được hỗ trợ:</b>\n{list_}"
    )


@app.on_message(filters.command(["assembly"], COMMAND_HANDLER))
@app.on_edited_message(filters.command(["assembly"], COMMAND_HANDLER))
async def assembly(_, message):
    if len(message.command) < 2:
        return await message.reply("Vui lòng nhập mã bạn muốn chạy.")
    res = await glot(message.command[0], "asm", message.text.split(None, 1)[1])
    hasil = res["stdout"] or res["stderr"]
    hasil = f"Result :\n{hasil}"
    try:
        return await message.reply(hasil, parse_mode=enums.ParseMode.DISABLED)
    except MessageTooLong:
        post = await rentry(hasil)
        return await message.reply(f"<b>Xem kết quả trong Rentry:</b>\n{post}")
    except Exception as e:
        return await message.reply(e, parse_mode=enums.ParseMode.DISABLED)


@app.on_message(filters.command(["ats"], COMMAND_HANDLER))
@app.on_edited_message(filters.command(["ats"], COMMAND_HANDLER))
async def ats(_, message):
    if len(message.command) < 2:
        return await message.reply("Vui lòng nhập mã bạn muốn chạy.")
    res = await glot(message.command[0], "dats", message.text.split(None, 1)[1])
    hasil = res["stdout"] or res["stderr"]
    hasil = f"Result :\n{hasil}"
    try:
        return await message.reply(hasil, parse_mode=enums.ParseMode.DISABLED)
    except MessageTooLong:
        post = await rentry(hasil)
        return await message.reply(f"<b>Xem kết quả trong Rentry:</b>\n{post}")
    except Exception as e:
        return await message.reply(e, parse_mode=enums.ParseMode.DISABLED)


@app.on_message(filters.command(["bash"], COMMAND_HANDLER))
@app.on_edited_message(filters.command(["bash"], COMMAND_HANDLER))
async def bash(_, message):
    if len(message.command) < 2:
        return await message.reply("Vui lòng nhập mã bạn muốn chạy.")
    res = await glot(message.command[0], "sh", message.text.split(None, 1)[1])
    hasil = res["stdout"] or res["stderr"]
    hasil = f"Result :\n{hasil}"
    try:
        return await message.reply(hasil, parse_mode=enums.ParseMode.DISABLED)
    except MessageTooLong:
        post = await rentry(hasil)
        return await message.reply(f"<b>Xem kết quả trong Rentry:</b>\n{post}")
    except Exception as e:
        return await message.reply(e, parse_mode=enums.ParseMode.DISABLED)


@app.on_message(filters.command(["c"], COMMAND_HANDLER))
@app.on_edited_message(filters.command(["c"], COMMAND_HANDLER))
async def c(_, message):
    if len(message.command) < 2:
        return await message.reply("Vui lòng nhập mã bạn muốn chạy.")
    res = await glot(message.command[0], "c", message.text.split(None, 1)[1])
    hasil = res["stdout"] or res["stderr"]
    hasil = f"Result :\n{hasil}"
    try:
        return await message.reply(hasil, parse_mode=enums.ParseMode.DISABLED)
    except MessageTooLong:
        post = await rentry(hasil)
        return await message.reply(f"<b>Xem kết quả trong Rentry:</b>\n{post}")
    except Exception as e:
        return await message.reply(e, parse_mode=enums.ParseMode.DISABLED)


@app.on_message(filters.command(["clojure"], COMMAND_HANDLER))
@app.on_edited_message(filters.command(["clojure"], COMMAND_HANDLER))
async def clojure(_, message):
    if len(message.command) < 2:
        return await message.reply("Vui lòng nhập mã bạn muốn chạy.")
    res = await glot(message.command[0], "clj", message.text.split(None, 1)[1])
    hasil = res["stdout"] or res["stderr"]
    hasil = f"Result :\n{hasil}"
    try:
        return await message.reply(hasil, parse_mode=enums.ParseMode.DISABLED)
    except MessageTooLong:
        post = await rentry(hasil)
        return await message.reply(f"<b>Xem kết quả trong Rentry:</b>\n{post}")
    except Exception as e:
        return await message.reply(e, parse_mode=enums.ParseMode.DISABLED)


@app.on_message(filters.command(["cobol"], COMMAND_HANDLER))
@app.on_edited_message(filters.command(["cobol"], COMMAND_HANDLER))
async def cobol(_, message):
    if len(message.command) < 2:
        return await message.reply("Vui lòng nhập mã bạn muốn chạy.")
    res = await glot(message.command[0], "cob", message.text.split(None, 1)[1])
    hasil = res["stdout"] or res["stderr"]
    hasil = f"Result :\n{hasil}"
    try:
        return await message.reply(hasil, parse_mode=enums.ParseMode.DISABLED)
    except MessageTooLong:
        post = await rentry(hasil)
        return await message.reply(f"<b>Xem kết quả trong Rentry:</b>\n{post}")
    except Exception as e:
        return await message.reply(e, parse_mode=enums.ParseMode.DISABLED)


@app.on_message(filters.command(["coffeescript"], COMMAND_HANDLER))
@app.on_edited_message(filters.command(["coffeescript"], COMMAND_HANDLER))
async def coffeescript(_, message):
    if len(message.command) < 2:
        return await message.reply("Vui lòng nhập mã bạn muốn chạy.")
    res = await glot(message.command[0], "coffee", message.text.split(None, 1)[1])
    hasil = res["stdout"] or res["stderr"]
    hasil = f"Result :\n{hasil}"
    try:
        return await message.reply(hasil, parse_mode=enums.ParseMode.DISABLED)
    except MessageTooLong:
        post = await rentry(hasil)
        return await message.reply(f"<b>Xem kết quả trong Rentry:</b>\n{post}")
    except Exception as e:
        return await message.reply(e, parse_mode=enums.ParseMode.DISABLED)


@app.on_message(filters.command(["cpp"], COMMAND_HANDLER))
@app.on_edited_message(filters.command(["cpp"], COMMAND_HANDLER))
async def cpp(_, message):
    if len(message.command) < 2:
        return await message.reply("Vui lòng nhập mã bạn muốn chạy.")
    res = await glot(message.command[0], "cpp", message.text.split(None, 1)[1])
    hasil = res["stdout"] or res["stderr"]
    hasil = f"Result :\n{hasil}"
    try:
        return await message.reply(hasil, parse_mode=enums.ParseMode.DISABLED)
    except MessageTooLong:
        post = await rentry(hasil)
        return await message.reply(f"<b>Xem kết quả trong Rentry:</b>\n{post}")
    except Exception as e:
        return await message.reply(e, parse_mode=enums.ParseMode.DISABLED)


@app.on_message(filters.command(["crystal"], COMMAND_HANDLER))
@app.on_edited_message(filters.command(["crystal"], COMMAND_HANDLER))
async def crystal(_, message):
    if len(message.command) < 2:
        return await message.reply("Vui lòng nhập mã bạn muốn chạy.")
    res = await glot(message.command[0], "cr", message.text.split(None, 1)[1])
    hasil = res["stdout"] or res["stderr"]
    hasil = f"Result :\n{hasil}"
    try:
        return await message.reply(hasil, parse_mode=enums.ParseMode.DISABLED)
    except MessageTooLong:
        post = await rentry(hasil)
        return await message.reply(f"<b>Xem kết quả trong Rentry:</b>\n{post}")
    except Exception as e:
        return await message.reply(e, parse_mode=enums.ParseMode.DISABLED)


@app.on_message(filters.command(["csharp"], COMMAND_HANDLER))
@app.on_edited_message(filters.command(["csharp"], COMMAND_HANDLER))
async def csharp(_, message):
    if len(message.command) < 2:
        return await message.reply("Vui lòng nhập mã bạn muốn chạy.")
    res = await glot(message.command[0], "cs", message.text.split(None, 1)[1])
    hasil = res["stdout"] or res["stderr"]
    hasil = f"Result :\n{hasil}"
    try:
        return await message.reply(hasil, parse_mode=enums.ParseMode.DISABLED)
    except MessageTooLong:
        post = await rentry(hasil)
        return await message.reply(f"<b>Xem kết quả trong Rentry:</b>\n{post}")
    except Exception as e:
        return await message.reply(e, parse_mode=enums.ParseMode.DISABLED)


@app.on_message(filters.command(["d"], COMMAND_HANDLER))
@app.on_edited_message(filters.command(["d"], COMMAND_HANDLER))
async def d(_, message):
    if len(message.command) < 2:
        return await message.reply("Vui lòng nhập mã bạn muốn chạy.")
    res = await glot(message.command[0], "d", message.text.split(None, 1)[1])
    hasil = res["stdout"] or res["stderr"]
    hasil = f"Result :\n{hasil}"
    try:
        return await message.reply(hasil, parse_mode=enums.ParseMode.DISABLED)
    except MessageTooLong:
        post = await rentry(hasil)
        return await message.reply(f"<b>Xem kết quả trong Rentry:</b>\n{post}")
    except Exception as e:
        return await message.reply(e, parse_mode=enums.ParseMode.DISABLED)


@app.on_message(filters.command(["elixir"], COMMAND_HANDLER))
@app.on_edited_message(filters.command(["elixir"], COMMAND_HANDLER))
async def elixir(_, message):
    if len(message.command) < 2:
        return await message.reply("Vui lòng nhập mã bạn muốn chạy.")
    res = await glot(message.command[0], "ex", message.text.split(None, 1)[1])
    hasil = res["stdout"] or res["stderr"]
    hasil = f"Result :\n{hasil}"
    try:
        return await message.reply(hasil, parse_mode=enums.ParseMode.DISABLED)
    except MessageTooLong:
        post = await rentry(hasil)
        return await message.reply(f"<b>Xem kết quả trong Rentry:</b>\n{post}")
    except Exception as e:
        return await message.reply(e, parse_mode=enums.ParseMode.DISABLED)


@app.on_message(filters.command(["elm"], COMMAND_HANDLER))
@app.on_edited_message(filters.command(["elm"], COMMAND_HANDLER))
async def elm(_, message):
    if len(message.command) < 2:
        return await message.reply("Vui lòng nhập mã bạn muốn chạy.")
    res = await glot(message.command[0], "elm", message.text.split(None, 1)[1])
    hasil = res["stdout"] or res["stderr"]
    hasil = f"Result :\n{hasil}"
    try:
        return await message.reply(hasil, parse_mode=enums.ParseMode.DISABLED)
    except MessageTooLong:
        post = await rentry(hasil)
        return await message.reply(f"<b>Xem kết quả trong Rentry:</b>\n{post}")
    except Exception as e:
        return await message.reply(e, parse_mode=enums.ParseMode.DISABLED)


@app.on_message(filters.command(["erlang"], COMMAND_HANDLER))
@app.on_edited_message(filters.command(["erlang"], COMMAND_HANDLER))
async def erlang(_, message):
    if len(message.command) < 2:
        return await message.reply("Vui lòng nhập mã bạn muốn chạy.")
    res = await glot(message.command[0], "erl", message.text.split(None, 1)[1])
    hasil = res["stdout"] or res["stderr"]
    hasil = f"Result :\n{hasil}"
    try:
        return await message.reply(hasil, parse_mode=enums.ParseMode.DISABLED)
    except MessageTooLong:
        post = await rentry(hasil)
        return await message.reply(f"<b>Xem kết quả trong Rentry:</b>\n{post}")
    except Exception as e:
        return await message.reply(e, parse_mode=enums.ParseMode.DISABLED)


@app.on_message(filters.command(["fsharp"], COMMAND_HANDLER))
@app.on_edited_message(filters.command(["fsharp"], COMMAND_HANDLER))
async def fsharp(_, message):
    if len(message.command) < 2:
        return await message.reply("Vui lòng nhập mã bạn muốn chạy.")
    res = await glot(message.command[0], "fs", message.text.split(None, 1)[1])
    hasil = res["stdout"] or res["stderr"]
    hasil = f"Result :\n{hasil}"
    try:
        return await message.reply(hasil, parse_mode=enums.ParseMode.DISABLED)
    except MessageTooLong:
        post = await rentry(hasil)
        return await message.reply(f"<b>Xem kết quả trong Rentry:</b>\n{post}")
    except Exception as e:
        return await message.reply(e, parse_mode=enums.ParseMode.DISABLED)


@app.on_message(filters.command(["go"], COMMAND_HANDLER))
@app.on_edited_message(filters.command(["go"], COMMAND_HANDLER))
async def go(_, message):
    if len(message.command) < 2:
        return await message.reply("Vui lòng nhập mã bạn muốn chạy.")
    res = await glot(message.command[0], "go", message.text.split(None, 1)[1])
    hasil = res["stdout"] or res["stderr"]
    hasil = f"Result :\n{hasil}"
    try:
        return await message.reply(hasil, parse_mode=enums.ParseMode.DISABLED)
    except MessageTooLong:
        post = await rentry(hasil)
        return await message.reply(f"<b>Xem kết quả trong Rentry:</b>\n{post}")
    except Exception as e:
        return await message.reply(e, parse_mode=enums.ParseMode.DISABLED)


@app.on_message(filters.command(["groovy"], COMMAND_HANDLER))
@app.on_edited_message(filters.command(["groovy"], COMMAND_HANDLER))
async def groovy(_, message):
    if len(message.command) < 2:
        return await message.reply("Vui lòng nhập mã bạn muốn chạy.")
    res = await glot(message.command[0], "groovy", message.text.split(None, 1)[1])
    hasil = res["stdout"] or res["stderr"]
    hasil = f"Result :\n{hasil}"
    try:
        return await message.reply(hasil, parse_mode=enums.ParseMode.DISABLED)
    except MessageTooLong:
        post = await rentry(hasil)
        return await message.reply(f"<b>Xem kết quả trong Rentry:</b>\n{post}")
    except Exception as e:
        return await message.reply(e, parse_mode=enums.ParseMode.DISABLED)


@app.on_message(filters.command(["haskell"], COMMAND_HANDLER))
@app.on_edited_message(filters.command(["haskell"], COMMAND_HANDLER))
async def haskell(_, message):
    if len(message.command) < 2:
        return await message.reply("Vui lòng nhập mã bạn muốn chạy.")
    res = await glot(message.command[0], "hs", message.text.split(None, 1)[1])
    hasil = res["stdout"] or res["stderr"]
    hasil = f"Result :\n{hasil}"
    try:
        return await message.reply(hasil, parse_mode=enums.ParseMode.DISABLED)
    except MessageTooLong:
        post = await rentry(hasil)
        return await message.reply(f"<b>Xem kết quả trong Rentry:</b>\n{post}")
    except Exception as e:
        return await message.reply(e, parse_mode=enums.ParseMode.DISABLED)


@app.on_message(filters.command(["idris"], COMMAND_HANDLER))
@app.on_edited_message(filters.command(["idris"], COMMAND_HANDLER))
async def idris(_, message):
    if len(message.command) < 2:
        return await message.reply("Vui lòng nhập mã bạn muốn chạy.")
    res = await glot(message.command[0], "idr", message.text.split(None, 1)[1])
    hasil = res["stdout"] or res["stderr"]
    hasil = f"Result :\n{hasil}"
    try:
        return await message.reply(hasil, parse_mode=enums.ParseMode.DISABLED)
    except MessageTooLong:
        post = await rentry(hasil)
        return await message.reply(f"<b>Xem kết quả trong Rentry:</b>\n{post}")
    except Exception as e:
        return await message.reply(e, parse_mode=enums.ParseMode.DISABLED)


@app.on_message(filters.command(["java"], COMMAND_HANDLER))
@app.on_edited_message(filters.command(["java"], COMMAND_HANDLER))
async def java(_, message):
    if len(message.command) < 2:
        return await message.reply("Vui lòng nhập mã bạn muốn chạy.")
    res = await glot(message.command[0], "java", message.text.split(None, 1)[1])
    hasil = res["stdout"] or res["stderr"]
    hasil = f"Result :\n{hasil}"
    try:
        return await message.reply(hasil, parse_mode=enums.ParseMode.DISABLED)
    except MessageTooLong:
        post = await rentry(hasil)
        return await message.reply(f"<b>Xem kết quả trong Rentry:</b>\n{post}")
    except Exception as e:
        return await message.reply(e, parse_mode=enums.ParseMode.DISABLED)


@app.on_message(filters.command(["javascript"], COMMAND_HANDLER))
@app.on_edited_message(filters.command(["javascript"], COMMAND_HANDLER))
async def javascript(_, message):
    if len(message.command) < 2:
        return await message.reply("Vui lòng nhập mã bạn muốn chạy.")
    res = await glot(message.command[0], "js", message.text.split(None, 1)[1])
    hasil = res["stdout"] or res["stderr"]
    hasil = f"Result :\n{hasil}"
    try:
        return await message.reply(hasil, parse_mode=enums.ParseMode.DISABLED)
    except MessageTooLong:
        post = await rentry(hasil)
        return await message.reply(f"<b>Xem kết quả trong Rentry:</b>\n{post}")
    except Exception as e:
        return await message.reply(e, parse_mode=enums.ParseMode.DISABLED)


@app.on_message(filters.command(["julia"], COMMAND_HANDLER))
@app.on_edited_message(filters.command(["julia"], COMMAND_HANDLER))
async def julia(_, message):
    if len(message.command) < 2:
        return await message.reply("Vui lòng nhập mã bạn muốn chạy.")
    res = await glot(message.command[0], "jl", message.text.split(None, 1)[1])
    hasil = res["stdout"] or res["stderr"]
    hasil = f"Result :\n{hasil}"
    try:
        return await message.reply(hasil, parse_mode=enums.ParseMode.DISABLED)
    except MessageTooLong:
        post = await rentry(hasil)
        return await message.reply(f"<b>Xem kết quả trong Rentry:</b>\n{post}")
    except Exception as e:
        return await message.reply(e, parse_mode=enums.ParseMode.DISABLED)


@app.on_message(filters.command(["kotlin"], COMMAND_HANDLER))
@app.on_edited_message(filters.command(["kotlin"], COMMAND_HANDLER))
async def kotlin(_, message):
    if len(message.command) < 2:
        return await message.reply("Vui lòng nhập mã bạn muốn chạy.")
    res = await glot(message.command[0], "kt", message.text.split(None, 1)[1])
    hasil = res["stdout"] or res["stderr"]
    hasil = f"Result :\n{hasil}"
    try:
        return await message.reply(hasil, parse_mode=enums.ParseMode.DISABLED)
    except MessageTooLong:
        post = await rentry(hasil)
        return await message.reply(f"<b>Xem kết quả trong Rentry:</b>\n{post}")
    except Exception as e:
        return await message.reply(e, parse_mode=enums.ParseMode.DISABLED)


@app.on_message(filters.command(["lua"], COMMAND_HANDLER))
@app.on_edited_message(filters.command(["lua"], COMMAND_HANDLER))
async def lua(_, message):
    if len(message.command) < 2:
        return await message.reply("Vui lòng nhập mã bạn muốn chạy.")
    res = await glot(message.command[0], "lua", message.text.split(None, 1)[1])
    hasil = res["stdout"] or res["stderr"]
    hasil = f"Result :\n{hasil}"
    try:
        return await message.reply(hasil, parse_mode=enums.ParseMode.DISABLED)
    except MessageTooLong:
        post = await rentry(hasil)
        return await message.reply(f"<b>Xem kết quả trong Rentry:</b>\n{post}")
    except Exception as e:
        return await message.reply(e, parse_mode=enums.ParseMode.DISABLED)


@app.on_message(filters.command(["mercury"], COMMAND_HANDLER))
@app.on_edited_message(filters.command(["mercury"], COMMAND_HANDLER))
async def mercury(_, message):
    if len(message.command) < 2:
        return await message.reply("Vui lòng nhập mã bạn muốn chạy.")
    res = await glot(message.command[0], "m", message.text.split(None, 1)[1])
    hasil = res["stdout"] or res["stderr"]
    hasil = f"Result :\n{hasil}"
    try:
        return await message.reply(hasil, parse_mode=enums.ParseMode.DISABLED)
    except MessageTooLong:
        post = await rentry(hasil)
        return await message.reply(f"<b>Xem kết quả trong Rentry:</b>\n{post}")
    except Exception as e:
        return await message.reply(e, parse_mode=enums.ParseMode.DISABLED)


@app.on_message(filters.command(["nim"], COMMAND_HANDLER))
@app.on_edited_message(filters.command(["nim"], COMMAND_HANDLER))
async def nim(_, message):
    if len(message.command) < 2:
        return await message.reply("Vui lòng nhập mã bạn muốn chạy.")
    res = await glot(message.command[0], "nim", message.text.split(None, 1)[1])
    hasil = res["stdout"] or res["stderr"]
    hasil = f"Result :\n{hasil}"
    try:
        return await message.reply(hasil, parse_mode=enums.ParseMode.DISABLED)
    except MessageTooLong:
        post = await rentry(hasil)
        return await message.reply(f"<b>Xem kết quả trong Rentry:</b>\n{post}")
    except Exception as e:
        return await message.reply(e, parse_mode=enums.ParseMode.DISABLED)


@app.on_message(filters.command(["nix"], COMMAND_HANDLER))
@app.on_edited_message(filters.command(["nix"], COMMAND_HANDLER))
async def nix(_, message):
    if len(message.command) < 2:
        return await message.reply("Vui lòng nhập mã bạn muốn chạy.")
    res = await glot(message.command[0], "nix", message.text.split(None, 1)[1])
    hasil = res["stdout"] or res["stderr"]
    hasil = f"Result :\n{hasil}"
    try:
        return await message.reply(hasil, parse_mode=enums.ParseMode.DISABLED)
    except MessageTooLong:
        post = await rentry(hasil)
        return await message.reply(f"<b>Xem kết quả trong Rentry:</b>\n{post}")
    except Exception as e:
        return await message.reply(e, parse_mode=enums.ParseMode.DISABLED)


@app.on_message(filters.command(["ocaml"], COMMAND_HANDLER))
@app.on_edited_message(filters.command(["ocaml"], COMMAND_HANDLER))
async def ocaml(_, message):
    if len(message.command) < 2:
        return await message.reply("Vui lòng nhập mã bạn muốn chạy.")
    res = await glot(message.command[0], "ml", message.text.split(None, 1)[1])
    hasil = res["stdout"] or res["stderr"]
    hasil = f"Result :\n{hasil}"
    try:
        return await message.reply(hasil, parse_mode=enums.ParseMode.DISABLED)
    except MessageTooLong:
        post = await rentry(hasil)
        return await message.reply(f"<b>Xem kết quả trong Rentry:</b>\n{post}")
    except Exception as e:
        return await message.reply(e, parse_mode=enums.ParseMode.DISABLED)


@app.on_message(filters.command(["perl"], COMMAND_HANDLER))
@app.on_edited_message(filters.command(["perl"], COMMAND_HANDLER))
async def perl(_, message):
    if len(message.command) < 2:
        return await message.reply("Vui lòng nhập mã bạn muốn chạy.")
    res = await glot(message.command[0], "pl", message.text.split(None, 1)[1])
    hasil = res["stdout"] or res["stderr"]
    hasil = f"Result :\n{hasil}"
    try:
        return await message.reply(hasil, parse_mode=enums.ParseMode.DISABLED)
    except MessageTooLong:
        post = await rentry(hasil)
        return await message.reply(f"<b>Xem kết quả trong Rentry:</b>\n{post}")
    except Exception as e:
        return await message.reply(e, parse_mode=enums.ParseMode.DISABLED)


@app.on_message(filters.command(["php"], COMMAND_HANDLER))
@app.on_edited_message(filters.command(["php"], COMMAND_HANDLER))
async def php(_, message):
    if len(message.command) < 2:
        return await message.reply("Vui lòng nhập mã bạn muốn chạy.")
    res = await glot(message.command[0], "php", message.text.split(None, 1)[1])
    hasil = res["stdout"] or res["stderr"]
    hasil = f"Result :\n{hasil}"
    try:
        return await message.reply(hasil, parse_mode=enums.ParseMode.DISABLED)
    except MessageTooLong:
        post = await rentry(hasil)
        return await message.reply(f"<b>Xem kết quả trong Rentry:</b>\n{post}")
    except Exception as e:
        return await message.reply(e, parse_mode=enums.ParseMode.DISABLED)


@app.on_message(filters.command(["python"], COMMAND_HANDLER))
@app.on_edited_message(filters.command(["python"], COMMAND_HANDLER))
async def python(_, message):
    if len(message.command) < 2:
        return await message.reply("Vui lòng nhập mã bạn muốn chạy.")
    res = await glot(message.command[0], "py", message.text.split(None, 1)[1])
    hasil = res["stdout"] or res["stderr"]
    hasil = f"Result :\n{hasil}"
    try:
        return await message.reply(hasil, parse_mode=enums.ParseMode.DISABLED)
    except MessageTooLong:
        post = await rentry(hasil)
        return await message.reply(f"<b>Xem kết quả trong Rentry:</b>\n{post}")
    except Exception as e:
        return await message.reply(e, parse_mode=enums.ParseMode.DISABLED)


@app.on_message(filters.command(["raku"], COMMAND_HANDLER))
@app.on_edited_message(filters.command(["raku"], COMMAND_HANDLER))
async def raku(_, message):
    if len(message.command) < 2:
        return await message.reply("Vui lòng nhập mã bạn muốn chạy.")
    res = await glot(message.command[0], "raku", message.text.split(None, 1)[1])
    hasil = res["stdout"] or res["stderr"]
    hasil = f"Result :\n{hasil}"
    try:
        return await message.reply(hasil, parse_mode=enums.ParseMode.DISABLED)
    except MessageTooLong:
        post = await rentry(hasil)
        return await message.reply(f"<b>Xem kết quả trong Rentry:</b>\n{post}")
    except Exception as e:
        return await message.reply(e, parse_mode=enums.ParseMode.DISABLED)


@app.on_message(filters.command(["ruby"], COMMAND_HANDLER))
@app.on_edited_message(filters.command(["ruby"], COMMAND_HANDLER))
async def ruby(_, message):
    if len(message.command) < 2:
        return await message.reply("Vui lòng nhập mã bạn muốn chạy.")
    res = await glot(message.command[0], "rb", message.text.split(None, 1)[1])
    hasil = res["stdout"] or res["stderr"]
    hasil = f"Result :\n{hasil}"
    try:
        return await message.reply(hasil, parse_mode=enums.ParseMode.DISABLED)
    except MessageTooLong:
        post = await rentry(hasil)
        return await message.reply(f"<b>Xem kết quả trong Rentry:</b>\n{post}")
    except Exception as e:
        return await message.reply(e, parse_mode=enums.ParseMode.DISABLED)


@app.on_message(filters.command(["rust"], COMMAND_HANDLER))
@app.on_edited_message(filters.command(["rust"], COMMAND_HANDLER))
async def rust(_, message):
    if len(message.command) < 2:
        return await message.reply("Vui lòng nhập mã bạn muốn chạy.")
    res = await glot(message.command[0], "rs", message.text.split(None, 1)[1])
    hasil = res["stdout"] or res["stderr"]
    hasil = f"Result :\n{hasil}"
    try:
        return await message.reply(hasil, parse_mode=enums.ParseMode.DISABLED)
    except MessageTooLong:
        post = await rentry(hasil)
        return await message.reply(f"<b>Xem kết quả trong Rentry:</b>\n{post}")
    except Exception as e:
        return await message.reply(e, parse_mode=enums.ParseMode.DISABLED)


@app.on_message(filters.command(["scala"], COMMAND_HANDLER))
@app.on_edited_message(filters.command(["scala"], COMMAND_HANDLER))
async def scala(_, message):
    if len(message.command) < 2:
        return await message.reply("Vui lòng nhập mã bạn muốn chạy.")
    res = await glot(message.command[0], "scala", message.text.split(None, 1)[1])
    hasil = res["stdout"] or res["stderr"]
    hasil = f"Result :\n{hasil}"
    try:
        return await message.reply(hasil, parse_mode=enums.ParseMode.DISABLED)
    except MessageTooLong:
        post = await rentry(hasil)
        return await message.reply(f"<b>Xem kết quả trong Rentry:</b>\n{post}")
    except Exception as e:
        return await message.reply(e, parse_mode=enums.ParseMode.DISABLED)


@app.on_message(filters.command(["swift"], COMMAND_HANDLER))
@app.on_edited_message(filters.command(["swift"], COMMAND_HANDLER))
async def swift(_, message):
    if len(message.command) < 2:
        return await message.reply("Vui lòng nhập mã bạn muốn chạy.")
    res = await glot(message.command[0], "swift", message.text.split(None, 1)[1])
    hasil = res["stdout"] or res["stderr"]
    hasil = f"Result :\n{hasil}"
    try:
        return await message.reply(hasil, parse_mode=enums.ParseMode.DISABLED)
    except MessageTooLong:
        post = await rentry(hasil)
        return await message.reply(f"<b>Xem kết quả trong Rentry:</b>\n{post}")
    except Exception as e:
        return await message.reply(e, parse_mode=enums.ParseMode.DISABLED)


@app.on_message(filters.command(["typescript"], COMMAND_HANDLER))
@app.on_edited_message(filters.command(["typescript"], COMMAND_HANDLER))
async def typescript(_, message):
    if len(message.command) < 2:
        return await message.reply("Vui lòng nhập mã bạn muốn chạy.")
    res = await glot(message.command[0], "ts", message.text.split(None, 1)[1])
    hasil = res["stdout"] or res["stderr"]
    hasil = f"Result :\n{hasil}"
    try:
        return await message.reply(hasil, parse_mode=enums.ParseMode.DISABLED)
    except MessageTooLong:
        post = await rentry(hasil)
        return await message.reply(f"<b>Xem kết quả trong Rentry:</b>\n{post}")
    except Exception as e:
        return await message.reply(e, parse_mode=enums.ParseMode.DISABLED)
