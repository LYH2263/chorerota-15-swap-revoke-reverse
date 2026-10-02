"""Revoke write path: roll back one confirmed swap and persist the result.

Raises RevokeError with a stable machine-readable code — the same string is
handed to the API client as `detail`, so backend and frontend share one
error vocabulary:
  swap_not_found   (404)  no such swap request
  not_confirmed    (400)  pending or already-revoked swaps cannot be revoked
  slot_touched:<ids> (409) later confirmed swap(s) moved one of the slots;
                           fail-fast, no cascade — revoke the blockers first
  slot_missing     (400)  the week grid no longer contains the slot
  same_assignee    (400)  grid state drifted, reverse swap would be a no-op
"""
from app.engines.revoke import find_blockers, reverse_swap


class RevokeError(Exception):
    def __init__(self, code: str):
        super().__init__(code)
        self.code = code


def revoke_swap(c, swap_id: int) -> dict:
    row = c.execute("SELECT * FROM swap_requests WHERE id=?", (swap_id,)).fetchone()
    if not row:
        raise RevokeError("swap_not_found")
    sw = dict(row)
    if sw["status"] != "confirmed":
        raise RevokeError("not_confirmed")

    siblings = [dict(r) for r in c.execute(
        "SELECT * FROM swap_requests WHERE week_id=?", (sw["week_id"],))]
    blockers = find_blockers(siblings, sw)
    if blockers:
        raise RevokeError("slot_touched:" + ",".join(str(i) for i in blockers))

    assigns = [dict(r) for r in c.execute(
        "SELECT id,day,task_id,member_id FROM assignments WHERE week_id=?", (sw["week_id"],))]
    slots = [{"day": a["day"], "task_id": a["task_id"], "member_id": a["member_id"]} for a in assigns]
    try:
        new_slots = reverse_swap(slots, sw)
    except ValueError as e:
        raise RevokeError(str(e))

    for a, s in zip(assigns, new_slots):
        c.execute("UPDATE assignments SET member_id=? WHERE id=?", (s["member_id"], a["id"]))
    c.execute("UPDATE swap_requests SET status='revoked' WHERE id=?", (swap_id,))
    c.commit()
    return {"ok": True, "swap_id": swap_id, "status": "revoked"}
