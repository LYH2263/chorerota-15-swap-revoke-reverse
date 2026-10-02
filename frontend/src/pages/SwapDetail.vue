<template>
  <div>
    <h1 class="brand">对调详情</h1>
    <p><router-link to="/swaps" class="muted">← 返回对调列表</router-link></p>
    <p v-if="err" class="err">{{ err }}</p>
    <div v-if="d" class="week-card">
      <header>
        #{{ d.id }} · 第 {{ d.week_id }} 周
        <span class="chip" :class="{ coral: d.status==='pending', revoked: d.status==='revoked' }">
          {{ statusLabel(d.status) }}
        </span>
      </header>
      <p>A 格：Day {{ d.a_day }} / Task {{ d.a_task }} —
        当前 <span class="chip coral">{{ d.a_current ? d.a_current.member_name : '格位已不存在' }}</span>
      </p>
      <p>B 格：Day {{ d.b_day }} / Task {{ d.b_task }} —
        当前 <span class="chip coral">{{ d.b_current ? d.b_current.member_name : '格位已不存在' }}</span>
      </p>
      <p v-if="d.note" class="muted">备注：{{ d.note }}</p>
      <button v-if="d.status==='confirmed'" @click="revoke">撤销此对调</button>
      <p v-if="d.status==='revoked'" class="muted">已撤销：两格成员已按反向交换恢复。</p>
    </div>
  </div>
</template>
<script setup>
import { ref, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { api } from '../api'
import { describeSwapError, SWAP_STATUS_LABELS } from '../swapErrors'
const route = useRoute()
const d = ref(null)
const err = ref('')
const statusLabel = s => SWAP_STATUS_LABELS[s] || s
async function load() {
  err.value = ''
  try { d.value = await api('/swaps/' + route.params.id) }
  catch (e) { err.value = describeSwapError(e.message) }
}
async function revoke() {
  err.value = ''
  try { await api('/swaps/' + route.params.id + '/revoke', { method: 'POST', body: '{}' }); await load() }
  catch (e) { err.value = describeSwapError(e.message) }
}
onMounted(load)
</script>
