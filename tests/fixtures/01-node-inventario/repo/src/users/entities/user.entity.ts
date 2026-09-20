@Entity('usuarios')
export class User {
  @Column({ length: 80 }) nome: string;
  @Column({ unique: true }) email: string;
  @Column({ name: 'data_nascimento' }) dataNascimento: Date;
  @Column() cpf: string;
  @Column({ name: 'telefone_celular' }) telefoneCelular: string;
}
