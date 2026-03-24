import { ref } from 'vue'

const messages = ref([])
let nextId = 0

export function useFlash() {
  function flash(text, category = 'success') {
    const id = nextId++
    messages.value.push({ id, text, category })
    setTimeout(() => {
      messages.value = messages.value.filter(m => m.id !== id)
    }, 5000)
  }

  function dismiss(id) {
    messages.value = messages.value.filter(m => m.id !== id)
  }

  return { messages, flash, dismiss }
}
