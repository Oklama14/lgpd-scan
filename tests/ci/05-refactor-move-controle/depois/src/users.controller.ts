@Controller("users")
export class UsersController {
  @Get("me") me() {}
  @Patch("me") atualizar() {}
}
