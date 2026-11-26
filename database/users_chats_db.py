from datetime import datetime, timezone

from database import AsyncIterList, execute, fetch, fetchrow, fetchval


class UsersData:
    """User/chat storage on Postgres.

    Was MongoDB (AsyncClient) with collections "userlist", "groups" and
    "member_history" in DATABASE_NAME. The pool is shared (database.get_pool);
    uri/database_name are accepted for signature compatibility but unused.
    """

    def __init__(self, uri=None, database_name=None):
        pass

    @staticmethod
    def new_user(id, name):
        return dict(
            id=id,
            name=name,
            ban_status=dict(
                is_banned=False,
                ban_reason="",
            ),
        )

    @staticmethod
    def new_group(id, title):
        return dict(
            id=id,
            title=title,
            chat_status=dict(
                is_disabled=False,
                reason="",
            ),
        )

    async def add_user(self, id, name):
        user = self.new_user(id, name)
        await execute(
            "INSERT INTO kk_userlist (id, name, ban_status) VALUES ($1, $2, $3) "
            "ON CONFLICT (id) DO NOTHING",
            user["id"],
            user["name"],
            user["ban_status"],
        )

    async def is_user_exist(self, id):
        row = await fetchrow("SELECT id FROM kk_userlist WHERE id = $1", int(id))
        return bool(row)

    async def total_users_count(self):
        return await fetchval("SELECT COUNT(*) FROM kk_userlist")

    async def remove_ban(self, id):
        return await execute("DELETE FROM kk_user_bans WHERE user_id = $1", id)

    async def ban_user(self, user_id, ban_reason="No Reason"):
        await execute(
            "INSERT INTO kk_user_bans (user_id, reason) VALUES ($1, $2) "
            "ON CONFLICT (user_id) DO UPDATE SET reason = EXCLUDED.reason",
            user_id,
            ban_reason,
        )

    async def get_ban_status(self, id):
        row = await fetchrow(
            "SELECT user_id, reason FROM kk_user_bans WHERE user_id = $1", int(id)
        )
        if row:
            return True, {"_id": row["user_id"], "reason": row["reason"]}
        return False, None

    async def get_all_users(self):
        rows = await fetch("SELECT id, name, ban_status FROM kk_userlist")
        bans = await fetch("SELECT user_id, reason FROM kk_user_bans")
        out = [
            {
                "_id": r["id"],
                "id": r["id"],
                "name": r["name"],
                "ban_status": dict(r["ban_status"]),
            }
            for r in rows
        ]
        out += [{"_id": b["user_id"], "reason": b["reason"]} for b in bans]
        return AsyncIterList(out)

    async def delete_user(self, user_id):
        await execute("DELETE FROM kk_userlist WHERE id = $1", int(user_id))

    async def is_chat_exist(self, id):
        row = await fetchrow("SELECT id FROM kk_groups WHERE id = $1", int(id))
        return bool(row)

    async def get_chat(self, chat):
        row = await fetchrow(
            "SELECT chat_status FROM kk_groups WHERE id = $1", int(chat)
        )
        return dict(row["chat_status"]) if row else False

    async def get_banned(self):
        users = await fetch(
            "SELECT id FROM kk_userlist "
            "WHERE (ban_status->>'is_banned')::boolean IS TRUE"
        )
        chats = await fetch(
            "SELECT id FROM kk_groups "
            "WHERE (chat_status->>'is_disabled')::boolean IS TRUE"
        )
        b_chats = [chat["id"] for chat in chats]
        b_users = [user["id"] for user in users]
        return b_users, b_chats

    async def add_chat(self, chat, title):
        group = self.new_group(chat, title)
        await execute(
            "INSERT INTO kk_groups (id, title, chat_status) VALUES ($1, $2, $3) "
            "ON CONFLICT (id) DO NOTHING",
            group["id"],
            group["title"],
            group["chat_status"],
        )

    async def re_enable_chat(self, id):
        chat_status = dict(
            is_disabled=False,
            reason="",
        )
        await execute(
            "UPDATE kk_groups SET chat_status = $1 WHERE id = $2", chat_status, int(id)
        )

    async def disable_chat(self, chat, reason="No Reason"):
        chat_status = dict(
            is_disabled=True,
            reason=reason,
        )
        await execute(
            "UPDATE kk_groups SET chat_status = $1 WHERE id = $2",
            chat_status,
            int(chat),
        )

    async def total_chat_count(self):
        return await fetchval("SELECT COUNT(*) FROM kk_groups")

    async def get_all_chats(self):
        rows = await fetch("SELECT id, title, chat_status FROM kk_groups")
        return AsyncIterList(
            [
                {
                    "_id": r["id"],
                    "id": r["id"],
                    "title": r["title"],
                    "chat_status": dict(r["chat_status"]),
                }
                for r in rows
            ]
        )

    async def get_db_size(self):
        return await fetchval("SELECT pg_database_size(current_database())")

    async def get_all_gbanned_users(self):
        rows = await fetch("SELECT user_id FROM kk_gban")
        return AsyncIterList([{"user_id": r["user_id"]} for r in rows])

    # Các hàm quản lý lịch sử tham gia
    async def log_member_join(self, chat_id: int, user_id: int):
        now = datetime.now(timezone.utc)
        await execute(
            "INSERT INTO kk_member_history (chat_id, user_id, first_joined, last_joined, join_count) "
            "VALUES ($1, $2, $3, $3, 1) "
            "ON CONFLICT (chat_id, user_id) DO UPDATE SET "
            "last_joined = EXCLUDED.last_joined, "
            "join_count = kk_member_history.join_count + 1, "
            "first_joined = COALESCE(kk_member_history.first_joined, EXCLUDED.first_joined)",
            chat_id,
            user_id,
            now,
        )

    async def log_member_leave(self, chat_id: int, user_id: int):
        await execute(
            "INSERT INTO kk_member_history (chat_id, user_id, last_left) VALUES ($1, $2, $3) "
            "ON CONFLICT (chat_id, user_id) DO UPDATE SET last_left = EXCLUDED.last_left",
            chat_id,
            user_id,
            datetime.now(timezone.utc),
        )

    async def has_joined_before(self, chat_id: int, user_id: int) -> int:
        row = await fetchrow(
            "SELECT join_count FROM kk_member_history WHERE chat_id = $1 AND user_id = $2",
            chat_id,
            user_id,
        )
        return row["join_count"] if row else 0

    async def get_member_history(self, chat_id: int, user_id: int):
        row = await fetchrow(
            "SELECT chat_id, user_id, first_joined, last_joined, last_left, join_count "
            "FROM kk_member_history WHERE chat_id = $1 AND user_id = $2",
            chat_id,
            user_id,
        )
        return dict(row) if row else {}


db = UsersData()


class PeersData:
    """Peer storage (was MongoDB 'peers' in the KaitoKidBot database).

    Kept for API compatibility. Pyrogram no longer persists peers anywhere
    now that its mongodb parameter is gone, so kk_peers stays empty unless
    something writes to it.
    """

    def __init__(self, uri=None, database_name=None):
        pass

    async def get_all_peers(self):
        rows = await fetch("SELECT id, data FROM kk_peers")
        out = []
        for r in rows:
            d = dict(r["data"] or {})
            d.setdefault("_id", r["id"])
            out.append(d)
        return AsyncIterList(out)


peers_db = PeersData()
