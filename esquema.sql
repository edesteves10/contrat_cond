DROP TABLE IF EXISTS contrat_cond;

CREATE TABLE contrat_cond (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    created TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    nome TEXT NOT NULL,
    cnpj TEXT NOT NULL,
    endereco TEXT NOT NULL,
    cep TEXT NOT NULL,
    estado TEXT NOT NULL,
    telefone TEXT NOT NULL,
    email TEXT NOT NULL,
    valor_contrato REAL NOT NULL,
    inicio_contrato TEXT NOT NULL,
    termino_contrato TEXT
);