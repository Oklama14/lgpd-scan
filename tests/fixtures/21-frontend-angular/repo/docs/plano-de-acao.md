# Plano de ação de segurança

1. Tirar o token do localStorage: hoje o login faz `localStorage.setItem('token', res.token)`.
2. Configurar Content-Security-Policy no servidor.
3. Trocar a fonte de https://fonts.googleapis.com por uma cópia local.
4. Avaliar um banner de cookie-consent antes do gtag.
