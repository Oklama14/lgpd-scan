export function intercept() {
  const authToken = authService.getToken();
  return authToken;
}
