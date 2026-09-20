@Entity('usuarios')
export class User {
  @Column() email: string;
  @Column() cpf: string;
}
