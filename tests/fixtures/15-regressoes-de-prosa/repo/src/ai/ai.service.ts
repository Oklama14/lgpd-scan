export class AiService {
  build(dto) {
    const instrucao = dto.instrucao ?? 'Escreva no máximo um único parágrafo.';
    return instrucao;
  }
}
