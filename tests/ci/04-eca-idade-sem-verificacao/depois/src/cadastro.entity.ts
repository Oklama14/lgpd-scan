@Entity("cadastros")
export class Cadastro {
  @Column({ name: "data_nascimento" }) dataNascimento: Date;
  @Column({ name: "maior_de_idade" }) maiorDeIdade: boolean;
}
