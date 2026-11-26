from database import execute, fetchrow


# Kiểm tra xem chức năng báo cáo link có được bật trong nhóm không
async def is_report_link_enabled(chat_id: int) -> bool:
    row = await fetchrow(
        "SELECT report_link_enabled FROM kk_report_links WHERE chat_id = $1", chat_id
    )
    return bool(row and row["report_link_enabled"])


# Bật/tắt chức năng báo cáo link
async def toggle_report_link(chat_id: int):
    row = await fetchrow(
        "SELECT report_link_enabled FROM kk_report_links WHERE chat_id = $1", chat_id
    )
    if row and row["report_link_enabled"]:
        await execute(
            "UPDATE kk_report_links SET report_link_enabled = FALSE WHERE chat_id = $1",
            chat_id,
        )
        return False
    else:
        await execute(
            "INSERT INTO kk_report_links (chat_id, report_link_enabled) VALUES ($1, TRUE) "
            "ON CONFLICT (chat_id) DO UPDATE SET report_link_enabled = TRUE",
            chat_id,
        )
        return True


# Lưu danh sách link loại trừ (whitelist)
async def set_excluded_links(chat_id: int, links: list):
    await execute(
        "INSERT INTO kk_report_links (chat_id, excluded_links) VALUES ($1, $2) "
        "ON CONFLICT (chat_id) DO UPDATE SET excluded_links = EXCLUDED.excluded_links",
        chat_id,
        links,
    )


# Lấy danh sách link loại trừ
async def get_excluded_links(chat_id: int) -> list:
    row = await fetchrow(
        "SELECT excluded_links FROM kk_report_links WHERE chat_id = $1", chat_id
    )
    return list(row["excluded_links"]) if row else []
