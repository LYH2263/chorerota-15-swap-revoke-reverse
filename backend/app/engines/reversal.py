"""Pure reversal logic for a confirmed swap.

A confirmed swap exchanged two slots; revoking it exchanges them back.
Everything here is side-effect free so it can be unit-tested against
hand-computed grids.
"""

from app.engines.rota import find_slot

# Reasons shared with the persistence layer / API so the error vocabulary
# is identical on both sides of the stack.
REVOKE_OK = "ok"
ERR_NOT_CONFIRMED = "not_confirmed"        # pending (or any non-confirmed row)
ERR_ALREADY_REVOKED = "already_revoked"
ERR_SLOT_MISSING = "slot_missing"          # grid no longer contains A or B
ERR_SNAPSHOT_UNAVAILABLE = "snapshot_unavailable"  # legacy row, no member snapshot
ERR_REVOKE_CONFLICT = "revoke_conflict"    # a later swap already touched A/B


def reverse_precondition(slots: list[dict], sw: dict) -> dict:
    """Decide whether swap ``sw`` can be reversed against the live grid.

    ``sw`` must carry the member snapshot taken at confirm time:
    ``a_member`` (occupant of A before the swap) and ``b_member``.
    Revocation is legal only when both slots still exist and their current
    occupants are exactly what this swap wrote — i.e. no later swap has
    touched either slot. Because a legal swap always changes both
    occupants, a later swap touching A or B is detected precisely.
    """
    if sw.get("a_member") is None or sw.get("b_member") is None:
        return {"ok": False, "reason": ERR_SNAPSHOT_UNAVAILABLE}
    sa = find_slot(slots, sw["a_day"], sw["a_task"])
    sb = find_slot(slots, sw["b_day"], sw["b_task"])
    if sa is None or sb is None:
        return {"ok": False, "reason": ERR_SLOT_MISSING}
    # After confirming S, A holds b_member and B holds a_member.
    if sa["member_id"] != sw["b_member"] or sb["member_id"] != sw["a_member"]:
        return {"ok": False, "reason": ERR_REVOKE_CONFLICT}
    return {"ok": True, "reason": REVOKE_OK}


def reverse_swap(slots: list[dict], sw: dict) -> list[dict]:
    """Return a new grid with swap ``sw`` reversed (A/B occupants swapped back)."""
    check = reverse_precondition(slots, sw)
    if not check["ok"]:
        raise ValueError(check["reason"])
    out = [dict(s) for s in slots]
    ia = next(i for i, s in enumerate(out) if s["day"] == sw["a_day"] and s["task_id"] == sw["a_task"])
    ib = next(i for i, s in enumerate(out) if s["day"] == sw["b_day"] and s["task_id"] == sw["b_task"])
    out[ia]["member_id"], out[ib]["member_id"] = out[ib]["member_id"], out[ia]["member_id"]
    return out
