<template>
  <div class="page-header">
    <div>
      <h1 class="page-title">История изменений</h1>
      <div v-if="employee" class="page-meta">{{ employee.full_name }}</div>
    </div>
    <router-link to="/" class="btn-ghost">Назад</router-link>
  </div>

  <div v-if="records.length" class="app-card">
    <table class="app-table">
      <thead>
        <tr>
          <th>Дата / время</th>
          <th>Событие</th>
          <th>Поле</th>
          <th>Было</th>
          <th>Стало</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="r in records" :key="r.id">
          <td style="color:var(--text-muted);white-space:nowrap">{{ formatDate(r.changed_at) }}</td>
          <td>
            <span :class="r.change_type === 'create' ? 'ev-create' : 'ev-update'">
              {{ r.change_type === 'create' ? 'Создание' : 'Изменение' }}
            </span>
          </td>
          <td>{{ fieldLabels[r.field_name] || r.field_name }}</td>
          <td>{{ r.old_value || '\u2014' }}</td>
          <td>{{ r.new_value || '\u2014' }}</td>
        </tr>
      </tbody>
    </table>
  </div>

  <div v-else class="app-card">
    <div class="empty-state">
      <p>История изменений отсутствует.</p>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { getHistory } from '../api/employees'
import { useFlash } from '../composables/useFlash'

const route = useRoute()
const router = useRouter()
const { flash } = useFlash()

const employee = ref(null)
const records = ref([])

const fieldLabels = {
  full_name: 'ФИО',
  position: 'Должность',
  department: 'Отдел',
  email: 'Email',
  phone: 'Телефон',
}

function formatDate(iso) {
  if (!iso) return ''
  const d = new Date(iso)
  return isNaN(d) ? iso : d.toLocaleString()
}

async function load() {
  try {
    const { data } = await getHistory(route.params.id)
    employee.value = data.employee
    records.value = data.records
  } catch (e) {
    if (e.response?.status === 404) {
      flash('Сотрудник не найден.', 'error')
      router.push('/')
    }
  }
}

onMounted(load)
</script>
