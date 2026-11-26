from async_pymongo import AsyncClient

from kaitokid.vars import DATABASE_NAME, DATABASE_URI

mongo = AsyncClient(DATABASE_URI)
dbname = mongo[DATABASE_NAME]
