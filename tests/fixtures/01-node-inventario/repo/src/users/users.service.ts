import * as bcrypt from 'bcryptjs';
export class UsersService {
  async create(dto) { const hash = await bcrypt.hash(dto.senha, 10); return hash; }
}
