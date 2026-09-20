@Entity('atendimentos')
export class Atendimento {
  @Column() cid: string;
  @Column({ name: 'cid_10' }) cid10: string;
  @Column() sorologia: string;
  @Column({ name: 'psicologo_responsavel_id' }) psicologoResponsavelId: number;
  @Column() cidade: string;
  @Column({ name: 'endereco_cidade' }) enderecoCidade: string;
}
