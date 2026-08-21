/**
 * The API answers in English, by design — it is a documented REST API — and the
 * owners read Portuguese. A duplicate name is the one failure they meet often
 * enough to be worth translating.
 *
 *     throw new Error(nameTaken(error, "um conjunto"));
 *
 * `what` is the noun with its article, because the sentence needs the gender:
 * "Já existe uma cor com esse nome" against "um conjunto". Three files had their
 * own copy of this, each with the noun baked in.
 */
export const nameTaken = (error, what) =>
    error.status === 409 ? `Já existe ${what} com esse nome.` : error.message;
