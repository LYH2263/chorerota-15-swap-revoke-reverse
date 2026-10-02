<template>
  <div v-if="s">
    <h1 class="brand">对调 #{{ s.id }}</h1>
    <p class="muted"><router-link to="/swaps">← 返回对调列表</router-link></p>
    <p v-if="err" class="err">{{ err }}</p>
    <div class="week-card">
      <div>
        状态：<span class="chip" :class="statusChip(s.status)">{{ s.status }}</span>
        <span class="muted"> · 第 {{ s.week_id }} 周</span>
      </div>
      <table style="margin-top:8px">
        <thead>
          <tr><th>格位</th><th>任务</th><th>确认前占用</th><th>当前占用</th></tr>
        </thead>
        <tbody>
          <tr>
            <td>A · D{{ s.a_day }}/T{{ s.a_task }}</td>
            <td>{{ s.a_task_title }}</td>
            <td>{{ s.a_member_name }}</td>
            <td>{{ s.a_current_member_name }}</td>
          </tr>
          <tr>
            <td>B · D{{ s.b_day }}/T{{ s.b_task }}</td>
            <td>{{ s.b_task_title }}</td>
            <td>{{ s.b_member_name }}</td>
            <td>{{ s.b_current_member_name }}</td>
          </tr>
        </tbody>
      </table>
      <p v-if="s.note" class="muted" style="margin-top:8px">备注：{{ s.note }}</p>
      <template v-if="s.status === 'confirmed'">
        <p v-if="s.revoke && !s.revoke.allowed" class="err">
          当前不可撤销：{{ swapMessage(s.revoke.reason) }}
        </p>
        <button :disabled="s.revoke && !s.revoke.allowed" style="margin-top:8px" @click="revoke">
          撤销该对调（反向交换恢复格位）
        </button>
      </template>
      <p v-else-if="s.status === 'revoked'" class="muted" style="margin-top:8px">
        该对调已撤销，格位已按反向交换恢复，不能再次撤销。
      </p>
      <p v-else class="muted" style="margin-top:8px">
        待确认单确认后才可以撤销；如要放弃请直接忽略或删除。
      </p>
    </div>
  </div>
  <div v-else><h1 class="brand">对调详情</h1><p class="err">{{ err || '加载中…' }}</p></div>
</template>
<script setup>
import { ref, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { api } from '../api'
import { swapMessage, swapError } from '../swapMessages'
const route = useRoute()
const s = ref(null)
const err = ref('')
function statusChip(status) {
  return { coral: status === 'pending', ghost: status === 'revoked' }
}
async function load() {
  err.value = ''
  try { s.value = await api('/swaps/' + route.params.id) }
  catch (e) { err.value = swapError(e) }
}
async function revoke() {
  err.value = ''
  try {
    await api('/swaps/' + route.params.id + '/revoke', { method: 'POST', body: '{}' })
    await load()
  } catch (e) {
    err.value = swapError(e)
    await load() // refresh occupants, e.g. 409 revoke_conflict may reflect a newer swap
  }
}
onMounted(load)
</script>
