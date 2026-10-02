// Machine-readable reasons from the backend -> user-facing Chinese text.
// Keep these keys in sync with app/engines/reversal.py and app/modules/swap_revoke/.
const MESSAGES = {
  not_pending: '只有待确认的对调才能确认',
  not_confirmed: '仅已确认的对调可以撤销（待确认单不能撤销）',
  already_revoked: '该对调已经撤销，不能重复撤销',
  revoke_conflict: '撤销失败：确认后又有对调动过这两格，需先处理后续对调',
  slot_missing: '撤销失败：格位已不存在（周表可能已重新生成）',
  snapshot_unavailable: '撤销失败：该对调缺少确认时的人员快照（历史数据）',
  slot_missing_request: '格位不存在，无法申请对调',
  same_assignee: '两格当前是同一人，无需对调',
  same_slot: '不能对调同一格',
  swap_not_found: '对调单不存在',
}

export function swapMessage(reason) {
  return MESSAGES[reason] || ('操作被拒绝：' + reason)
}

export function swapError(err) {
  // api() already lifts FastAPI's detail string into err.message.
  return swapMessage(err.message)
}
