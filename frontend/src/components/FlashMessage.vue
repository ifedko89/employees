<template>
  <div v-for="msg in messages" :key="msg.id"
       :class="['flash', msg.category === 'success' ? 'success' : 'error']">
    <span>{{ msg.text }}</span>
    <button class="flash-close" @click="dismiss(msg.id)" aria-label="Закрыть">&#10005;</button>
  </div>
</template>

<script setup>
import { useFlash } from '../composables/useFlash'

const { messages, dismiss } = useFlash()
</script>
