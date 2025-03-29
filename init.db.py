import sqlite3

def init_db():
    try:
        conn = sqlite3.connect('database.db')
        print("Banco de dados aberto com sucesso")

        with open('esquema.sql', 'r') as f:
            conn.executescript(f.read())
        print("Tabela criada com sucesso")

        conn.close()
    except sqlite3.Error as error:
        print("Erro ao executar script sql:", error)

if __name__ == '__main__':
    init_db()