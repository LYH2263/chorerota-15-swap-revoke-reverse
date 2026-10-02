// Backend returns machine-readable detail codes (see revoke_store.py);
// keep the Chinese wording here so list and detail pages stay consistent.
export function describeSwapError(msg) {
  if (!msg) return ''
  if (msg === 'not_confirmed') return '只有「已确认」的对调可以撤销（待确认或已撤销的单不可撤销）'
  if (msg.startsWith('slot_touched:')) {
    const ids = msg.slice('slot_touched:'.length).split(',').map(s => '#' + s).join('、')
    return `撤销失败：对调 ${ids} 在此之后确认且动过同一格，请先撤销它`
  }
  if (msg === 'slot_missing') return '撤销失败：格位已不存在（周表可能被重新生成）'
  if (msg === 'same_assignee') return '撤销失败：两格当前是同一成员，状态已漂移'
  if (msg === 'swap_not_found') return '对调单不存在'
  return msg
}

export const SWAP_STATUS_LABELS = { pending: '待确认', confirmed: '已确认', revoked: '已撤销' }
