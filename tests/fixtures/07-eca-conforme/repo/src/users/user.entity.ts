@Entity('usuarios')
export class User {
  @Column({ name: 'responsavel_id', nullable: true }) responsavelId: number | null;
  @Column({ name: 'faixa_etaria' }) faixaEtaria: string;
  @Column({ name: 'vinculo_responsavel_em', nullable: true }) vinculoResponsavelEm: Date;
}
