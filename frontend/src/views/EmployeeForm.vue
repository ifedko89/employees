<template>
  <div class="page-header">
    <div>
      <h1 class="page-title">{{ isEdit ? 'Редактировать сотрудника' : 'Новый сотрудник' }}</h1>
      <div v-if="isEdit && employee" class="page-meta">
        Создан: {{ formatDate(employee.created_at) }}
        <span v-if="employee.updated_at"> | Обновлён: {{ formatDate(employee.updated_at) }}</span>
      </div>
    </div>
    <router-link to="/" class="btn-ghost">Отмена</router-link>
  </div>

  <div class="app-card form-card">
    <form novalidate @submit.prevent="submit">
      <div class="mb-3">
        <label class="form-label">ФИО</label>
        <input v-model="form.full_name" type="text" name="full_name"
               :class="['form-control', errors.full_name && 'is-invalid']">
        <div class="invalid-feedback" v-if="errors.full_name">{{ errors.full_name }}</div>
      </div>

      <div class="mb-3">
        <label class="form-label">Должность</label>
        <select v-model="form.position_id" name="position"
                :class="['form-select', errors.position && 'is-invalid']">
          <option value="0" disabled>Выберите должность</option>
          <option v-for="p in positions" :key="p.id" :value="p.id">{{ p.name }}</option>
        </select>
        <div class="invalid-feedback" v-if="errors.position">{{ errors.position }}</div>
      </div>

      <div class="mb-3">
        <label class="form-label">Отдел</label>
        <select v-model="form.department_id" name="department"
                :class="['form-select', errors.department && 'is-invalid']">
          <option value="0" disabled>Выберите отдел</option>
          <option v-for="d in departments" :key="d.id" :value="d.id">{{ d.name }}</option>
        </select>
        <div class="invalid-feedback" v-if="errors.department">{{ errors.department }}</div>
      </div>

      <div class="mb-3">
        <label class="form-label">Email</label>
        <input v-model="form.email" type="email" name="email"
               :class="['form-control', errors.email && 'is-invalid']">
        <div class="invalid-feedback" v-if="errors.email">{{ errors.email }}</div>
      </div>

      <div class="mb-3">
        <label class="form-label">Телефон</label>
        <input v-model="form.phone" type="text" name="phone"
               :class="['form-control', errors.phone && 'is-invalid']">
        <div class="invalid-feedback" v-if="errors.phone">{{ errors.phone }}</div>
      </div>

      <button type="submit" class="btn-solid" :disabled="submitting">Сохранить</button>
    </form>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { getEmployee, createEmployee, updateEmployee } from '../api/employees'
import { useFlash } from '../composables/useFlash'

const route = useRoute()
const router = useRouter()
const { flash } = useFlash()

const isEdit = computed(() => route.name === 'edit')
const employee = ref(null)
const positions = ref([])
const departments = ref([])
const errors = ref({})
const submitting = ref(false)

const form = ref({
  full_name: '',
  position_id: 0,
  department_id: 0,
  email: '',
  phone: '',
})

function formatDate(iso) {
  if (!iso) return ''
  const d = new Date(iso)
  return isNaN(d) ? iso : d.toLocaleString()
}

async function loadData() {
  if (isEdit.value) {
    try {
      const { data } = await getEmployee(route.params.id)
      employee.value = data.employee
      positions.value = data.positions
      departments.value = data.departments
      form.value = {
        full_name: data.employee.full_name,
        position_id: data.employee.position_id,
        department_id: data.employee.department_id,
        email: data.employee.email,
        phone: data.employee.phone,
      }
    } catch (e) {
      if (e.response?.status === 404) {
        flash('Сотрудник не найден.', 'error')
        router.push('/')
      }
    }
  } else {
    const [posRes, deptRes] = await Promise.all([
      import('../api/positions').then(m => m.listPositions()),
      import('../api/departments').then(m => m.listDepartments()),
    ])
    positions.value = posRes.data.positions
    departments.value = deptRes.data.departments
  }
}

async function submit() {
  errors.value = {}
  submitting.value = true
  try {
    if (isEdit.value) {
      const { data } = await updateEmployee(route.params.id, form.value)
      flash(data.message, 'success')
    } else {
      const { data } = await createEmployee(form.value)
      flash(data.message, 'success')
    }
    router.push('/')
  } catch (e) {
    if (e.response?.status === 400 && e.response.data.errors) {
      errors.value = e.response.data.errors
    } else {
      flash('Произошла ошибка.', 'error')
    }
  } finally {
    submitting.value = false
  }
}

onMounted(loadData)
</script>
