export const nameTaken = (error, what) =>
    error.status === 409 ? `Já existe ${what} com esse nome.` : error.message;
