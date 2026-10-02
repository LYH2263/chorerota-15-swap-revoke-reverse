"""Reverse-swap engine: undo a confirmed swap on the slot grid.

Pure functions, no DB. A swap is an involution — exchanging the same two
slots' members again restores the pre-swap state — but only when no later
confirmed swap has touched either slot. `find_blockers` detects that case;
the store layer fails the revoke instead of cascading (拍板: fail-fast).
"""

def swap_slots(sw: dict) -> set[tuple[int, int]]:
    """The two endpoint slots of a swap request, as (day, task_id) pairs."""
    return {(sw["a_day"], sw["a_task"]), (sw["b_day"], sw["b_task"])}


def find_blockers(swaps: list[dict], target: dict) -> list[int]:
    """Ids of still-active swaps confirmed after `target` that share a slot.

    Only swaps confirmed later (confirmed_seq) can have moved the occupants
    of target's slots; earlier ones are already baked into the state target
    was confirmed against. Revoked swaps no longer occupy the grid.
    """
    t_slots = swap_slots(target)
    t_seq = target.get("confirmed_seq") or 0
    out = []
    for s in swaps:
        if s["id"] == target["id"] or s["status"] != "confirmed":
            continue
        if (s.get("confirmed_seq") or 0) <= t_seq:
            continue
        if swap_slots(s) & t_slots:
            out.append(s["id"])
    return sorted(out)


def reverse_swap(slots: list[dict], sw: dict) -> list[dict]:
    """Exchange the two endpoint slots' members back. Inverse of apply_swap."""
    idx = {(s["day"], s["task_id"]): i for i, s in enumerate(slots)}
    ia = idx.get((sw["a_day"], sw["a_task"]))
    ib = idx.get((sw["b_day"], sw["b_task"]))
    if ia is None or ib is None:
        raise ValueError("slot_missing")
    out = [dict(s) for s in slots]
    if out[ia]["member_id"] == out[ib]["member_id"]:
        raise ValueError("same_assignee")
    out[ia]["member_id"], out[ib]["member_id"] = out[ib]["member_id"], out[ia]["member_id"]
    return out
