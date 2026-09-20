@Entity('usuarios')
export class Usuario {
  @Column({ unique: true }) email: string;
}
