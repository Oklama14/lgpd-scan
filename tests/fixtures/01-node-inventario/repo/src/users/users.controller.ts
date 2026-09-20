@Controller('users')
export class UsersController {
  @Get('me') me(@Request() req) { return this.svc.find(req.user.id); }
  @Patch('me') update(@Body() dto: UpdateDto) { return this.svc.update(dto); }
  @Delete('me') remove(@Request() req) { return this.svc.deleteAccount(req.user.id); }
}
