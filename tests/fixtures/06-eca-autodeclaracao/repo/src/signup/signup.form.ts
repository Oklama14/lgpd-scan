export const signupForm = {
  nome: ['', Validators.required],
  dataNascimento: ['', Validators.required],
  souMaiorDeIdade: [false, mustBeTrue],
};
