"""Read-side aggregation for swap requests: list filtering and detail.

Separate from the revoke write path (``app.modules.swap_revoke``) and the
reverse engine (``app.engines.reversal``).
"""

from app.engines.reversal import reverse_precondition


def list_swaps(c, include_revoked: bool = False) -> list[dict]:
    """Return swap rows, newest first. Revoked rows are hidden by default."""
    sql = "SELECT * FROM swap_requests"
    if not include_revoked:
        sql += " WHERE status != 'revoked'"
    sql += " ORDER BY id DESC"
    return [dict(r) for r in c.execute(sql)]


def get_swap_detail(c, swap_id: int) -> dict | None:
    """Full detail for one swap (revoked rows included — detail stays openable).

    Adds member names, current slot occupants and, for a confirmed swap,
    ``revoke`` (``{allowed, reason}``) evaluated against the live board.
    """
    sw = c.execute("SELECT * FROM swap_requests WHERE id=?", (swap_id,)).fetchone()
    if not sw:
        return None
    sw = dict(sw)

    members = {r["id"]: r["name"] for r in c.execute("SELECT id,name FROM members")}
    tasks = {r["id"]: r["title"] for r in c.execute("SELECT id,title FROM tasks")}
    sw["a_member_name"] = members.get(sw.get("a_member"), "?")
    sw["b_member_name"] = members.get(sw.get("b_member"), "?")
    sw["a_task_title"] = tasks.get(sw["a_task"], "?")
    sw["b_task_title"] = tasks.get(sw["b_task"], "?")

    assigns = [dict(r) for r in c.execute(
        "SELECT day,task_id,member_id FROM assignments WHERE week_id=?", (sw["week_id"],))]
    cur = {(a["day"], a["task_id"]): a["member_id"] for a in assigns}
    sw["a_current_member"] = cur.get((sw["a_day"], sw["a_task"]))
    sw["b_current_member"] = cur.get((sw["b_day"], sw["b_task"]))
    sw["a_current_member_name"] = members.get(sw["a_current_member"], "?")
    sw["b_current_member_name"] = members.get(sw["b_current_member"], "?")

    if sw["status"] == "confirmed":
        check = reverse_precondition(
            assigns, sw)
        sw["revoke"] = {"allowed": check["ok"], "reason": check["reason"]}
    else:
        sw["revoke"] = None
    return sw
