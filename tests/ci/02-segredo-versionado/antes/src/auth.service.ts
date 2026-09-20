import * as bcrypt from "bcryptjs";
export class AuthService { async hash(s) { return bcrypt.hash(s, 10); } }
