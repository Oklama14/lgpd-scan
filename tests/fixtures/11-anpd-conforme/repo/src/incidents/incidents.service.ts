export class IncidentsService {
  async notificarAnpd(id: number) { return this.http.post('/anpd', { id }); }
}
