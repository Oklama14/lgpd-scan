@Entity('usuarios')
export class User {
  @Column() email: string;
  @Column({ name: 'data_nascimento' }) dataNascimento: Date;
}
