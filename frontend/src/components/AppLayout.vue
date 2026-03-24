<template>
  <nav class="app-nav">
    <div class="app-nav-inner">
      <router-link class="nav-brand" to="/">
        <span class="nav-brand-dot">E</span>
        Сотрудники
      </router-link>
      <span class="nav-spacer"></span>
      <div class="nav-dropdown">
        <button class="nav-link-item" type="button">Справочники &#9662;</button>
        <div class="nav-dropdown-menu">
          <router-link class="nav-dropdown-item" to="/positions">Должности</router-link>
          <router-link class="nav-dropdown-item" to="/departments">Отделы</router-link>
        </div>
      </div>
      <router-link to="/create" class="btn-nav-add">+ Добавить</router-link>
    </div>
  </nav>

  <div class="app-content">
    <FlashMessage />
    <router-view />
  </div>
</template>

<script setup>
import FlashMessage from './FlashMessage.vue'
</script>
