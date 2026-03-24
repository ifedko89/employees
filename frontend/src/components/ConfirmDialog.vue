<template>
  <Teleport to="body">
    <template v-if="visible">
      <div class="modal-backdrop" style="z-index:1050" @click="cancel"></div>
      <div class="modal-overlay" style="z-index:1055">
        <div class="modal-box">
          <p style="margin:0 0 20px;font-size:14px">{{ message }}</p>
          <div class="flex gap-2 justify-end">
            <button class="btn-ghost" @click="cancel">Отмена</button>
            <button class="btn-solid" style="background:var(--danger)" @click="confirm">Удалить</button>
          </div>
        </div>
      </div>
    </template>
  </Teleport>
</template>

<script setup>
import { ref } from 'vue'

const visible = ref(false)
const message = ref('')
let resolveFn = null

function open(msg) {
  message.value = msg
  visible.value = true
  return new Promise(resolve => { resolveFn = resolve })
}

function confirm() {
  visible.value = false
  resolveFn?.(true)
}

function cancel() {
  visible.value = false
  resolveFn?.(false)
}

defineExpose({ open })
</script>
