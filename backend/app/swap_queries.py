"""Read-side queries for swap requests: list filtering and detail.

The list hides revoked swaps by default; the detail endpoint has no filter
so a revoked swap stays openable by id.
"""

def list_swaps(c, include_revoked: bool = False) -> list[dict]:
    sql = "SELECT * FROM swap_requests"
    if not include_revoked:
        sql += " WHERE status != 'revoked'"
    sql += " ORDER BY id DESC"
    return [dict(r) for r in c.execute(sql)]


def get_swap_detail(c, swap_id: int) -> dict | None:
    row = c.execute("SELECT * FROM swap_requests WHERE id=?", (swap_id,)).fetchone()
    if not row:
        return None
    sw = dict(row)
    members = {r["id"]: r["name"] for r in c.execute("SELECT id,name FROM members")}

    def occupant(day: int, task: int) -> dict | None:
        r = c.execute(
            "SELECT member_id FROM assignments WHERE week_id=? AND day=? AND task_id=?",
            (sw["week_id"], day, task)).fetchone()
        if not r:
            return None
        return {"member_id": r["member_id"], "member_name": members.get(r["member_id"], "?")}

    sw["a_current"] = occupant(sw["a_day"], sw["a_task"])
    sw["b_current"] = occupant(sw["b_day"], sw["b_task"])
    return sw
