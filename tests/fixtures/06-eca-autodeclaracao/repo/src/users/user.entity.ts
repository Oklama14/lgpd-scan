@Entity('usuarios')
export class User {
  @Column({ name: 'data_nascimento' }) dataNascimento: Date;
  @Column({ name: 'eh_menor', default: false }) ehMenor: boolean;
}
