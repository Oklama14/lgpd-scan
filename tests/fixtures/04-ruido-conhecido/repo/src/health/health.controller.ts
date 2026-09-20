@Controller('health')
export class HealthController {
  @Get() check() { return { status: 'ok' }; }
}
