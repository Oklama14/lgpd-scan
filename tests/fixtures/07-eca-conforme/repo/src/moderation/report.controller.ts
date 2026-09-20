@Controller('denuncias')
export class ReportController {
  @Post() denunciarConteudo(@Body() dto: DenunciaDto) { return this.svc.takedown(dto); }
}
