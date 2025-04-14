CREATE TABLE ContratCond (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    created DATETIME DEFAULT CURRENT_TIMESTAMP,
    nome VARCHAR(200) NOT NULL,
    cnpj VARCHAR(14) UNIQUE NOT NULL,
    endereco VARCHAR(200) NOT NULL,
    cep VARCHAR(200) NOT NULL,
    estado VARCHAR(200) NOT NULL,
    telefone VARCHAR(200) NOT NULL,
    email VARCHAR(200) NOT NULL,
    valor_contrato REAL NOT NULL,
    inicio_contrato VARCHAR(200) NOT NULL,
    termino_contrato VARCHAR(200),
    abrangencia_contrato VARCHAR(200) NOT NULL
);