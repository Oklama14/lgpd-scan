@Controller('users')
export class UsersController {
  @Get('me') me(@Request() req) { return this.svc.find(req.user.id); }
}
