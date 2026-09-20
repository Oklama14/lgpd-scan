export class AgeVerificationService {
  async verify(doc: string) {
    return this.unicoCheck.documentCheck({ doc, liveness: true });
  }
}
