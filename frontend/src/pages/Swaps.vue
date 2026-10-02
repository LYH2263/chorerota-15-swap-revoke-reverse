<template>
  <div>
    <h1 class="brand">对调</h1>
    <p class="muted">先生成周表，再填写两格对调（day + task_id）</p>
    <div class="week-card" style="margin-bottom:12px">
      <label>A day <input type="number" v-model.number="form.a_day" /></label>
      <label>A task_id <input type="number" v-model.number="form.a_task" /></label>
      <label>B day <input type="number" v-model.number="form.b_day" /></label>
      <label>B task_id <input type="number" v-model.number="form.b_task" /></label>
      <button @click="request">申请对调</button>
    </div>
    <label class="muted" style="display:inline-block;margin-bottom:8px">
      <input type="checkbox" v-model="includeRevoked" @change="load" />
      显示已撤销（revoked）
    </label>
    <p v-if="err" class="err">{{ err }}</p>
    <ul class="list">
      <li v-for="s in rows" :key="s.id">
        <router-link :to="'/swaps/' + s.id">
          #{{ s.id }} D{{ s.a_day }}/T{{ s.a_task }} ↔ D{{ s.b_day }}/T{{ s.b_task }}
        </router-link>
        <span class="chip" :class="statusChip(s.status)">{{ s.status }}</span>
        <button v-if="s.status==='pending'" style="margin-left:8px" @click="confirm(s.id)">确认改表</button>
        <button v-else-if="s.status==='confirmed'" style="margin-left:8px" @click="revoke(s.id)">撤销</button>
      </li>
      <li v-if="!rows.length" class="muted">暂无对调</li>
    </ul>
  </div>
</template>
<script setup>
import { ref, onMounted } from 'vue'
import { api } from '../api'
import { swapError } from '../swapMessages'
const rows = ref([])
const err = ref('')
const includeRevoked = ref(false)
const form = ref({ a_day: 0, a_task: 1, b_day: 1, b_task: 1 })
function statusChip(status) {
  return { coral: status === 'pending', ghost: status === 'revoked' }
}
async function load() {
  err.value = ''
  try { rows.value = await api('/swaps?include_revoked=' + includeRevoked.value) }
  catch (e) { err.value = swapError(e) }
}
async function request() {
  err.value = ''
  try {
    await api('/weeks/1/swaps', { method: 'POST', body: JSON.stringify(form.value) })
    await load()
  } catch (e) { err.value = swapError(e) }
}
async function confirm(id) {
  err.value = ''
  try {
    await api('/swaps/' + id + '/confirm', { method: 'POST', body: '{}' })
    await load()
  } catch (e) { err.value = swapError(e) }
}
async function revoke(id) {
  err.value = ''
  try {
    await api('/swaps/' + id + '/revoke', { method: 'POST', body: '{}' })
    await load()
  } catch (e) { err.value = swapError(e) }
}
onMounted(load)
</script>
