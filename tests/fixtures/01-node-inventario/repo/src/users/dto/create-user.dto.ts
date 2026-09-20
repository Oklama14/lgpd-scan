export class CreateUserDto {
  @IsString() nomeCompleto: string;
  @IsEmail() email: string;
}
