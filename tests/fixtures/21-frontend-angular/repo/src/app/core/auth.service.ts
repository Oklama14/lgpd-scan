import { Injectable, inject } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { tap } from 'rxjs';

@Injectable({ providedIn: 'root' })
export class AuthService {
  private http = inject(HttpClient);

  login(email: string, senha: string) {
    return this.http.post<{ token: string }>('/api/auth/login', { email, senha }).pipe(
      tap((res) => localStorage.setItem('token', res.token)),
    );
  }

  salvarTema(tema: string) {
    localStorage.setItem('theme', tema);
  }

  // localStorage.setItem('token_antigo', valor) -- removido na versao 2
  sair() {
    localStorage.removeItem('token');
  }
}
