@Controller('titular')
export class DsarController {
  // prazo_resposta: 15 dias
  @Post('solicitacao-titular') criar(@Body() dto: SolicitacaoTitularDto) {
    return this.svc.abrir(dto, { prazoResposta: 15 });
  }
}
