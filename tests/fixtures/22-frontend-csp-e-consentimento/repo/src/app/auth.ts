export function guardarPreferencias(idioma: string) {
  localStorage.setItem('idioma', idioma);
  sessionStorage.setItem('ultima_pagina', location.pathname);
}
