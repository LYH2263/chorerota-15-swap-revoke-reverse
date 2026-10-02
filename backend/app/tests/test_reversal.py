from app.engines.rota import build_week_slots, apply_swap
from app.engines.reversal import reverse_swap, reverse_precondition, ERR_REVOKE_CONFLICT


def _grid():
    # day then task: day0 -> [(0,t1,m1),(0,t2,m2),(0,t3,m3)], day1 likewise
    return build_week_slots([1, 2, 3], [10, 20, 30], days=2)


def test_reverse_restores_original_grid():
    slots = _grid()
    before = [dict(s) for s in slots]
    after = apply_swap(slots, 0, 10, 0, 20)  # m1 <-> m2
    sw = {"a_day": 0, "a_task": 10, "b_day": 0, "b_task": 20,
          "a_member": 1, "b_member": 2}
    assert reverse_precondition(after, sw)["ok"] is True
    restored = reverse_swap(after, sw)
    # hand-computable: reverse is just the same exchange applied again
    assert restored == before
    assert restored[0]["member_id"] == 1 and restored[1]["member_id"] == 2


def test_reverse_conflict_when_later_swap_touched_slot():
    slots = _grid()
    sw = {"a_day": 0, "a_task": 10, "b_day": 0, "b_task": 20,
          "a_member": 1, "b_member": 2}
    after_s = apply_swap(slots, 0, 10, 0, 20)
    # third swap T moves slot A (0,10) again: (0,10)m2 <-> (1,10)m1
    after_t = apply_swap(after_s, 0, 10, 1, 10)
    check = reverse_precondition(after_t, sw)
    assert check["ok"] is False and check["reason"] == ERR_REVOKE_CONFLICT
    try:
        reverse_swap(after_t, sw)
        assert False, "expected ValueError"
    except ValueError as e:
        assert str(e) == ERR_REVOKE_CONFLICT


def test_reverse_allowed_when_later_swap_touched_other_slots():
    slots = _grid()
    sw = {"a_day": 0, "a_task": 10, "b_day": 0, "b_task": 20,
          "a_member": 1, "b_member": 2}
    after_s = apply_swap(slots, 0, 10, 0, 20)
    # T only moves day-1 slots: (1,10)m1 <-> (1,20)m2
    after_t = apply_swap(after_s, 1, 10, 1, 20)
    assert reverse_precondition(after_t, sw)["ok"] is True
    restored = reverse_swap(after_t, sw)
    # S's two slots are back; T's day-1 change stays exactly as before
    assert restored[0]["member_id"] == 1 and restored[1]["member_id"] == 2
    assert restored[3]["member_id"] == 2 and restored[4]["member_id"] == 1
