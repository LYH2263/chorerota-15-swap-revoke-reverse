"""Persistence layer for revoking a confirmed swap.

Kept in its own module, separate from the pure reverse engine
(``app.engines.reversal``) and from list filtering
(``app.modules.swap_list``).
"""

from app.engines.reversal import (
    reverse_precondition,
    reverse_swap,
    ERR_NOT_CONFIRMED,
    ERR_ALREADY_REVOKED,
)

ERR_SWAP_NOT_FOUND = "swap_not_found"


class RevokeError(Exception):
    """Carries a machine-readable ``reason`` so the API and frontend share one vocabulary."""

    def __init__(self, reason: str, http_status: int = 400):
        super().__init__(reason)
        self.reason = reason
        self.http_status = http_status


def _load_grid(c, week_id: int) -> tuple[list, list[dict]]:
    assigns = [dict(r) for r in c.execute(
        "SELECT id,day,task_id,member_id FROM assignments WHERE week_id=?", (week_id,))]
    slots = [{"day": a["day"], "task_id": a["task_id"], "member_id": a["member_id"]}
             for a in assigns]
    return assigns, slots


def revoke_swap(c, swap_id: int) -> dict:
    """Reverse a confirmed swap on the same connection.

    Writes are left uncommitted so the caller owns the transaction.
    Raises :class:`RevokeError` with a stable ``reason`` on any rejection.
    """
    sw = c.execute("SELECT * FROM swap_requests WHERE id=?", (swap_id,)).fetchone()
    if not sw:
        raise RevokeError(ERR_SWAP_NOT_FOUND, http_status=404)
    sw = dict(sw)

    if sw["status"] == "revoked":
        raise RevokeError(ERR_ALREADY_REVOKED)
    if sw["status"] != "confirmed":
        # pending (or anything else that was never confirmed) cannot be revoked.
        raise RevokeError(ERR_NOT_CONFIRMED)

    assigns, slots = _load_grid(c, sw["week_id"])
    check = reverse_precondition(slots, sw)
    if not check["ok"]:
        # revoke_conflict / slot_missing: the live grid no longer matches what
        # this swap wrote (a later swap or regeneration moved a slot), so
        # reversal would corrupt the board -> 409.
        # snapshot_unavailable: legacy row with no member snapshot -> 422.
        status = 409 if check["reason"] in ("revoke_conflict", "slot_missing") else 422
        raise RevokeError(check["reason"], http_status=status)

    new_slots = reverse_swap(slots, sw)  # cannot raise: precondition passed
    for a, s in zip(assigns, new_slots):
        c.execute("UPDATE assignments SET member_id=? WHERE id=?", (s["member_id"], a["id"]))
    c.execute("UPDATE swap_requests SET status='revoked' WHERE id=?", (swap_id,))
    return {"ok": True, "swap_id": swap_id}
