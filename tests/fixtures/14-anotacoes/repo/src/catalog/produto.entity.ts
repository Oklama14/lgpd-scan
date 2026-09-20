@Entity('produtos')
export class Produto {
  // lgpd-scan: ignore personal_data_field — genero do produto, nao da pessoa
  @Column() genero: string;
  @Column() nome: string; // lgpd-scan: ignore personal_data_field — nome do produto
}
