<template>
  <form @submit.prevent="salvar">
    <input v-model="form.telefone" placeholder="Telefone">
    <input v-model="form.endereco" placeholder="Endereço">
  </form>
</template>

<script setup>
import { reactive } from 'vue';
const form = reactive({ telefone: '', endereco: '' });
</script>
