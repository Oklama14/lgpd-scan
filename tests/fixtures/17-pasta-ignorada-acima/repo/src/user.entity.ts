@Entity('usuarios')
export class Usuario {
  @Column({ length: 120, unique: true }) email: string;
  @Column() cpf: string;
  @Column({ name: 'data_nascimento' }) dataNascimento: Date;
}
