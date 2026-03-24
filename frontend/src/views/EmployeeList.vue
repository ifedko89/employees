<template>
  <div class="page-header">
    <h1 class="page-title">
      Сотрудники
      <span v-if="employees.length" class="count-pill">{{ employees.length }}</span>
    </h1>
  </div>

  <!-- Search & filter -->
  <div class="app-card search-bar">
    <form class="flex gap-2 items-end flex-wrap" @submit.prevent="fetch">
      <div style="flex:1;min-width:200px">
        <input v-model="query" type="text" class="form-control" name="q"
               placeholder="Поиск по имени, должности, отделу...">
      </div>
      <div style="min-width:180px">
        <select v-model="dept" class="form-select" @change="fetch">
          <option value="">Все отделы</option>
          <option v-for="d in departments" :key="d" :value="d">{{ d }}</option>
        </select>
      </div>
      <button type="submit" class="btn-solid">Найти</button>
      <button v-if="query || dept" type="button" class="btn-ghost" @click="reset">Сбросить</button>
    </form>
  </div>

  <!-- Table -->
  <div v-if="employees.length" class="app-card">
    <table class="app-table">
      <thead>
        <tr>
          <th><a href="#" @click.prevent="toggleSort('full_name')">ФИО {{ sortIcon('full_name') }}</a></th>
          <th><a href="#" @click.prevent="toggleSort('position')">Должность {{ sortIcon('position') }}</a></th>
          <th><a href="#" @click.prevent="toggleSort('department')">Отдел {{ sortIcon('department') }}</a></th>
          <th>Email</th>
          <th class="hide-mobile">Телефон</th>
          <th></th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="emp in employees" :key="emp.id">
          <td>{{ emp.full_name }}</td>
          <td>{{ emp.position }}</td>
          <td><span class="dept-tag">{{ emp.department }}</span></td>
          <td>{{ emp.email }}</td>
          <td class="hide-mobile">{{ emp.phone }}</td>
          <td style="white-space:nowrap">
            <router-link :to="`/edit/${emp.id}`" class="btn-act">Изменить</router-link>
            <router-link :to="`/history/${emp.id}`" class="btn-act history" style="margin-left:4px">История</router-link>
            <button class="btn-act danger" style="margin-left:4px" @click="confirmDelete(emp)">Удалить</button>
          </td>
        </tr>
      </tbody>
    </table>
  </div>

  <!-- Empty state -->
  <div v-else class="app-card">
    <div class="empty-state">
      <p v-if="query || dept">По заданным фильтрам ничего не найдено.</p>
      <p v-else>Сотрудников пока нет.</p>
      <button v-if="query || dept" class="btn-ghost" @click="reset">Показать всех</button>
      <router-link v-else to="/create" class="btn-solid">Добавить первого</router-link>
    </div>
  </div>

  <ConfirmDialog ref="dialog" />
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { listEmployees, deleteEmployee } from '../api/employees'
import { useFlash } from '../composables/useFlash'
import ConfirmDialog from '../components/ConfirmDialog.vue'

const { flash } = useFlash()

const employees = ref([])
const departments = ref([])
const query = ref('')
const sort = ref('full_name')
const order = ref('asc')
const dept = ref('')
const dialog = ref(null)

async function fetch() {
  const params = {}
  if (query.value) params.q = query.value
  if (sort.value) params.sort = sort.value
  if (order.value) params.order = order.value
  if (dept.value) params.dept = dept.value
  const { data } = await listEmployees(params)
  employees.value = data.employees
  departments.value = data.departments
}

function toggleSort(col) {
  if (sort.value === col) {
    order.value = order.value === 'asc' ? 'desc' : 'asc'
  } else {
    sort.value = col
    order.value = 'asc'
  }
  fetch()
}

function sortIcon(col) {
  if (sort.value !== col) return ''
  return order.value === 'asc' ? '\u2191' : '\u2193'
}

function reset() {
  query.value = ''
  dept.value = ''
  fetch()
}

async function confirmDelete(emp) {
  const ok = await dialog.value.open(`Удалить сотрудника «${emp.full_name}»?`)
  if (!ok) return
  await deleteEmployee(emp.id)
  flash(`Сотрудник «${emp.full_name}» удалён.`, 'success')
  fetch()
}

onMounted(fetch)
</script>
