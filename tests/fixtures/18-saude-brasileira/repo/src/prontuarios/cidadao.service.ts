export class CidadaoService {
  buscarPorCidade(cidade: string) { return this.repo.find({ where: { cidade } }); }
  validarCidadania(doc: string) { return doc.length > 0; }
}
