@Entity('usuarios')
export class User {
  // @lgpd:pii=cpf @lgpd:basis=consentimento
  @Column() cpf: string;
  // @lgpd:retention=5anos
  @Column() email: string;
  // lgpd-scan: ignore personal_data_field
  @Column() telefone: string;
  // lgpd-scan: ignore sinal_inexistente — motivo qualquer aqui
  @Column() celular: string;
}
