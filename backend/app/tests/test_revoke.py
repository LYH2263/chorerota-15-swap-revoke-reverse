"""Revoke flow: reversible rollback, pending rejection, conflict tradeoff.

Store-level tests run against a fresh sqlite DB per test (DATA_DIR points at
a tmp dir). They import no fastapi, so they also run under plain python3.
"""
import os
import tempfile

from app import seed
from app.db import connect
from app.engines.rota import build_week_slots, apply_swap
from app.engines.revoke import find_blockers, reverse_swap
from app.revoke_store import revoke_swap, RevokeError
from app.swap_queries import list_swaps, get_swap_detail


def _fresh_db():
    os.environ["DATA_DIR"] = tempfile.mkdtemp()
    seed.init_db()
    return connect()


def _generate(c, week_id=1, days=7):
    """Mirror of main.generate's write path."""
    mids = [r["id"] for r in c.execute(
        "SELECT id FROM members WHERE active=1 AND data_quality='clean' ORDER BY id")]
    tids = [r["id"] for r in c.execute(
        "SELECT id FROM tasks WHERE data_quality='clean' AND weight>0 ORDER BY id")]
    slots = build_week_slots(mids, tids, days=days)
    c.execute("DELETE FROM assignments WHERE week_id=?", (week_id,))
    for s in slots:
        c.execute("INSERT INTO assignments(week_id,day,task_id,member_id) VALUES (?,?,?,?)",
                  (week_id, s["day"], s["task_id"], s["member_id"]))
    c.commit()
    return slots


def _request_swap(c, a_day, a_task, b_day, b_task, week_id=1):
    cur = c.execute(
        "INSERT INTO swap_requests(week_id,a_day,a_task,b_day,b_task,status,note)"
        " VALUES (?,?,?,?,?,?,?)",
        (week_id, a_day, a_task, b_day, b_task, "pending", ""))
    c.commit()
    return cur.lastrowid


def _confirm(c, sid, week_id=1):
    """Mirror of main.confirm_swap's write path (kept in sync by hand)."""
    sw = dict(c.execute("SELECT * FROM swap_requests WHERE id=?", (sid,)).fetchone())
    assigns = [dict(r) for r in c.execute(
        "SELECT id,day,task_id,member_id FROM assignments WHERE week_id=?", (week_id,))]
    slots = [{"day": a["day"], "task_id": a["task_id"], "member_id": a["member_id"]} for a in assigns]
    new_slots = apply_swap(slots, sw["a_day"], sw["a_task"], sw["b_day"], sw["b_task"])
    for a, s in zip(assigns, new_slots):
        c.execute("UPDATE assignments SET member_id=? WHERE id=?", (s["member_id"], a["id"]))
    seq = c.execute("SELECT COALESCE(MAX(confirmed_seq),0)+1 AS s FROM swap_requests").fetchone()["s"]
    c.execute("UPDATE swap_requests SET status='confirmed', confirmed_seq=? WHERE id=?", (seq, sid))
    c.commit()


def _board(c, week_id=1):
    return {(r["day"], r["task_id"]): r["member_id"] for r in c.execute(
        "SELECT day,task_id,member_id FROM assignments WHERE week_id=?", (week_id,))}


def _raises(code, fn, *args):
    try:
        fn(*args)
    except RevokeError as e:
        assert e.code == code or e.code.startswith(code), f"want {code}, got {e.code}"
        return
    raise AssertionError(f"expected RevokeError({code})")


# --- engine: reverse swap is the exact inverse of apply_swap (hand-checkable)

def test_reverse_swap_roundtrip_restores_grid():
    slots = build_week_slots([1, 2, 3], [10, 20, 30], days=7)
    sw = {"a_day": 0, "a_task": 10, "b_day": 0, "b_task": 20}
    swapped = apply_swap(slots, 0, 10, 0, 20)
    assert swapped != slots
    assert reverse_swap(swapped, sw) == [dict(s) for s in slots]


def test_reverse_swap_rejects_missing_slot():
    slots = [{"day": 0, "task_id": 1, "member_id": 9}]
    sw = {"a_day": 0, "a_task": 1, "b_day": 5, "b_task": 5}
    try:
        reverse_swap(slots, sw)
        raise AssertionError("expected ValueError")
    except ValueError as e:
        assert str(e) == "slot_missing"


def test_find_blockers_only_flags_later_overlapping_confirmed():
    target = {"id": 1, "status": "confirmed", "confirmed_seq": 1,
              "a_day": 0, "a_task": 1, "b_day": 0, "b_task": 2}
    others = [
        # later confirmed, shares slot (0,2) -> blocker
        {"id": 2, "status": "confirmed", "confirmed_seq": 2,
         "a_day": 0, "a_task": 2, "b_day": 1, "b_task": 1},
        # later confirmed but disjoint slots -> not a blocker
        {"id": 3, "status": "confirmed", "confirmed_seq": 3,
         "a_day": 2, "a_task": 1, "b_day": 2, "b_task": 2},
        # overlapping but already revoked -> not a blocker
        {"id": 4, "status": "revoked", "confirmed_seq": 4,
         "a_day": 0, "a_task": 1, "b_day": 3, "b_task": 3},
        # overlapping but confirmed earlier -> baked into target's state
        {"id": 5, "status": "confirmed", "confirmed_seq": 0,
         "a_day": 0, "a_task": 1, "b_day": 4, "b_task": 1},
    ]
    assert find_blockers([target] + others, target) == [2]


# --- store: reversible revoke

def test_revoke_confirmed_restores_board_and_marks_revoked():
    c = _fresh_db()
    _generate(c)
    before = _board(c)
    sid = _request_swap(c, 0, 1, 0, 2)
    _confirm(c, sid)
    assert _board(c) != before
    r = revoke_swap(c, sid)
    assert r["status"] == "revoked"
    assert _board(c) == before  # 看板回到撤销前格位，与手算反向交换一致
    sw = c.execute("SELECT status FROM swap_requests WHERE id=?", (sid,)).fetchone()
    assert sw["status"] == "revoked"
    # 详情也回到撤销前格位，且已撤销单仍可打开
    d = get_swap_detail(c, sid)
    assert d["status"] == "revoked"
    assert d["a_current"]["member_id"] == before[(0, 1)]
    assert d["b_current"]["member_id"] == before[(0, 2)]
    c.close()


def test_revoke_pending_and_revoked_rejected():
    c = _fresh_db()
    _generate(c)
    sid = _request_swap(c, 0, 1, 0, 2)
    _raises("not_confirmed", revoke_swap, c, sid)          # pending 拒撤
    _confirm(c, sid)
    revoke_swap(c, sid)
    _raises("not_confirmed", revoke_swap, c, sid)          # 已撤销不可再撤
    _raises("swap_not_found", revoke_swap, c, 9999)
    c.close()


# --- store: conflict tradeoff — fail-fast, manual LIFO chain

def test_revoke_conflict_fails_then_lifo_chain_unwinds():
    c = _fresh_db()
    _generate(c)
    before = _board(c)
    s1 = _request_swap(c, 0, 1, 0, 2)   # touches (0,1),(0,2)
    _confirm(c, s1)
    s2 = _request_swap(c, 0, 2, 0, 3)   # later, touches (0,2) — same slot as s1
    _confirm(c, s2)
    # 拍板: fail-fast — revoking s1 while s2 sits on its slot must fail
    _raises("slot_touched:2", revoke_swap, c, s1)
    assert _board(c) != before          # nothing was rolled back
    # manual cascade: revoke the blocker first, then s1 succeeds
    revoke_swap(c, s2)
    revoke_swap(c, s1)
    assert _board(c) == before
    c.close()


def test_revoke_not_blocked_by_disjoint_later_swap():
    c = _fresh_db()
    _generate(c)
    before = _board(c)
    s1 = _request_swap(c, 0, 1, 0, 2)
    _confirm(c, s1)
    s2 = _request_swap(c, 1, 1, 1, 2)   # later but disjoint slots
    _confirm(c, s2)
    revoke_swap(c, s1)                  # must succeed despite later s2
    assert _board(c)[(0, 1)] == before[(0, 1)]
    assert _board(c)[(0, 2)] == before[(0, 2)]
    c.close()


# --- queries: list filter hides revoked by default, detail stays open

def test_list_swaps_hides_revoked_by_default():
    c = _fresh_db()
    _generate(c)
    s1 = _request_swap(c, 0, 1, 0, 2)   # will be revoked
    s2 = _request_swap(c, 1, 1, 1, 2)   # stays pending
    s3 = _request_swap(c, 2, 1, 2, 2)   # stays confirmed
    _confirm(c, s1)
    _confirm(c, s3)
    revoke_swap(c, s1)
    visible = {r["id"] for r in list_swaps(c)}
    assert visible == {s2, s3}
    everything = {r["id"] for r in list_swaps(c, include_revoked=True)}
    assert everything == {s1, s2, s3}
    assert get_swap_detail(c, s1)["status"] == "revoked"  # 详情仍可打开
    c.close()


# --- migration: old DBs gain confirmed_seq with backfill

def test_migration_backfills_confirmed_seq():
    d = tempfile.mkdtemp()
    os.environ["DATA_DIR"] = d
    import sqlite3
    raw = sqlite3.connect(os.path.join(d, "chorerota.db"))
    raw.executescript("""
    CREATE TABLE swap_requests(id INTEGER PRIMARY KEY AUTOINCREMENT, week_id INT,
        a_day INT, a_task INT, b_day INT, b_task INT, status TEXT, note TEXT);
    INSERT INTO swap_requests(week_id,a_day,a_task,b_day,b_task,status,note)
        VALUES (1,0,1,0,2,'confirmed',''), (1,1,1,1,2,'pending',''), (1,2,1,2,2,'confirmed','');
    """)
    raw.commit(); raw.close()
    seed.init_db()
    c = connect()
    rows = c.execute("SELECT id,status,confirmed_seq FROM swap_requests ORDER BY id").fetchall()
    assert rows[0]["confirmed_seq"] == 1 and rows[1]["confirmed_seq"] is None
    assert rows[2]["confirmed_seq"] == 3  # id-order backfill, gaps fine
    c.close()
