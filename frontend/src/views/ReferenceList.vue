<template>
  <div class="page-header">
    <h1 class="page-title">{{ title }}</h1>
  </div>

  <div class="ref-grid">
    <!-- Left: form -->
    <div>
      <div class="app-card">
        <div class="app-card-header">
          <h2 class="app-card-title">{{ editItem ? 'Редактировать' : 'Добавить' }}</h2>
        </div>
        <div style="padding:16px 20px">
          <form @submit.prevent="submitForm">
            <input v-model="formName" type="text" name="name" class="form-control"
                   required minlength="2" maxlength="50" autofocus
                   :placeholder="editItem ? '' : 'Новое значение'">
            <div class="flex gap-2 mt-3">
              <button type="submit" class="btn-solid">{{ editItem ? 'Сохранить' : 'Добавить' }}</button>
              <button v-if="editItem" type="button" class="btn-ghost" @click="cancelEdit">Отмена</button>
            </div>
          </form>
        </div>
      </div>
    </div>

    <!-- Right: list -->
    <div>
      <div class="app-card">
        <div class="app-card-header">
          <h2 class="app-card-title">{{ title }}</h2>
          <span v-if="items.length" class="count-pill">{{ items.length }}</span>
        </div>
        <div v-if="items.length">
          <table class="app-table">
            <tbody>
              <tr v-for="item in items" :key="item.id">
                <td>{{ item.name }}</td>
                <td style="white-space:nowrap;text-align:right">
                  <a href="#" class="btn-act" @click.prevent="startEdit(item)">Изменить</a>
                  <button class="btn-act danger" style="margin-left:4px" @click="confirmDelete(item)">Удалить</button>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
        <div v-else class="empty-state">
          <p>Список пуст.</p>
        </div>
      </div>
    </div>
  </div>

  <ConfirmDialog ref="dialog" />
</template>

<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import { useRoute } from 'vue-router'
import * as positionsApi from '../api/positions'
import * as departmentsApi from '../api/departments'
import { useFlash } from '../composables/useFlash'
import ConfirmDialog from '../components/ConfirmDialog.vue'

const route = useRoute()
const { flash } = useFlash()

const type = computed(() => route.meta.type)
const title = computed(() => type.value === 'positions' ? 'Должности' : 'Отделы')
const listKey = computed(() => type.value === 'positions' ? 'positions' : 'departments')

const items = ref([])
const editItem = ref(null)
const formName = ref('')
const dialog = ref(null)

async function load() {
  const listFn = type.value === 'positions' ? positionsApi.listPositions : departmentsApi.listDepartments
  const { data } = await listFn()
  items.value = data[listKey.value]
}

function startEdit(item) {
  editItem.value = item
  formName.value = item.name
}

function cancelEdit() {
  editItem.value = null
  formName.value = ''
}

async function submitForm() {
  const name = formName.value.trim()
  if (!name) return

  try {
    if (editItem.value) {
      const updateFn = type.value === 'positions' ? positionsApi.updatePosition : departmentsApi.updateDepartment
      const { data } = await updateFn(editItem.value.id, name)
      flash(data.message, 'success')
      editItem.value = null
    } else {
      const createFn = type.value === 'positions' ? positionsApi.createPosition : departmentsApi.createDepartment
      const { data } = await createFn(name)
      flash(data.message, 'success')
    }
    formName.value = ''
    load()
  } catch (e) {
    const msg = e.response?.data?.error || 'Произошла ошибка.'
    flash(msg, 'error')
  }
}

async function confirmDelete(item) {
  const ok = await dialog.value.open(`Удалить «${item.name}»?`)
  if (!ok) return

  try {
    const deleteFn = type.value === 'positions' ? positionsApi.deletePosition : departmentsApi.deleteDepartment
    const { data } = await deleteFn(item.id)
    flash(data.message, 'success')
    load()
  } catch (e) {
    const msg = e.response?.data?.error || 'Произошла ошибка.'
    flash(msg, 'error')
  }
}

watch(type, () => {
  cancelEdit()
  load()
})

onMounted(load)
</script>
