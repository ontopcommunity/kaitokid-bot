import os
import time
from asyncio import get_event_loop
from faulthandler import enable as faulthandler_enable
from logging import ERROR, INFO, StreamHandler, basicConfig, getLogger, handlers

import uvloop
from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from pyrogram import Client

from kaitokid.vars import (
    API_HASH,
    API_ID,
    BOT_TOKEN,
    DATABASE_URI,
    TZ,
    USER_SESSION,
)

basicConfig(
    level=INFO,
    format="[%(levelname)s] - [%(asctime)s - %(name)s - %(message)s] -> [%(module)s:%(lineno)d]",
    datefmt="%d-%b-%y %H:%M:%S",
    handlers=[
        handlers.RotatingFileHandler(
            "KaitoKidLogs.txt", mode="w+", maxBytes=5242880, backupCount=1
        ),
        StreamHandler(),
    ],
)
getLogger("pyrogram").setLevel(ERROR)
getLogger("httpx").setLevel(ERROR)

MOD_LOAD = []
MOD_NOLOAD = []
HELPABLE = {}
cleanmode = {}
botStartTime = time.time()
kaitokid_version = "v3.0"

uvloop.install()
faulthandler_enable()
from kaitokid.core import kaitokid_patch

# Pyrogram Bot Client (no MongoDB peer storage; peers are resolved in-memory)
app = Client(
    "KaitoKidBot",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN,
    sleep_threshold=180,
    app_version="3.0",
    workers=50,
    max_concurrent_transmissions=4
)
app.log = getLogger("KaitoKid")

# Pyrogram UserBot Client
user = Client(
    "KaitoKidUbot",
    session_string=USER_SESSION,
    sleep_threshold=180,
    app_version="1.0"
)

# SQLAlchemy defaults postgresql:// to the psycopg (v3) driver, but only
# psycopg2-binary is installed. Force the psycopg2 dialect for the
# scheduler jobstore (asyncpg still uses the plain postgresql:// URL).
jobstores = {
    "default": SQLAlchemyJobStore(
        url=DATABASE_URI.replace("postgresql://", "postgresql+psycopg2://", 1)
    )
}
scheduler = AsyncIOScheduler(jobstores=jobstores, timezone=TZ)

app.start()
BOT_ID = app.me.id
BOT_NAME = app.me.first_name
BOT_USERNAME = app.me.username
if USER_SESSION:
    user.start()
    UBOT_ID = user.me.id
    UBOT_NAME = user.me.first_name
    UBOT_USERNAME = user.me.username
else:
    UBOT_ID = None
    UBOT_NAME = None
    UBOT_USERNAME = None
