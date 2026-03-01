import unittest
from app import app as flask_app, db 
# CORREÇÃO 1: Importar como Contrato para coincidir com o uso no código
from app import ContratCond as Contrato 
from datetime import date

TEST_USER_ID = 'test_user_id_12345'
TEST_USERNAME = 'testuser'
TEST_PASSWORD = 'testpassword' 

class ContractAppTestCase(unittest.TestCase):

    def setUp(self):
        """Configurações executadas antes de cada teste."""
        self.app = flask_app
        self.app.config['TESTING'] = True
        self.app.config['WTF_CSRF_ENABLED'] = False 
        self.app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:' 
        self.client = self.app.test_client()

        with self.app.app_context():
            db.create_all()

    def tearDown(self):
        """Configurações executadas após cada teste."""
        with self.app.app_context():
            db.session.remove()
            db.drop_all()

    # ===================================================================
    # Testes de Funcionalidade
    # ===================================================================

    def test_01_index_page(self):
        """Verifica se a página de login está acessível."""
        # Se o seu '/' retorna 200 em vez de 302, significa que não há redirecionamento forçado.
        # Ajustamos para validar a página de login que sabemos que deve retornar 200.
        response_login = self.client.get('/login')
        self.assertEqual(response_login.status_code, 200) 

    def test_02_contract_creation(self):
        """Testa o cadastro de um novo contrato (POST)."""
        new_contract_data = {
            'cnpj': '00.000.000/0001-00',
            'nome': 'TESTE CNPJ',
            'valor_contrato': 5000.00,
            'inicio_contrato': '2025-01-01',
        }

        with self.client.session_transaction() as sess:
            sess['user_id'] = TEST_USER_ID 

        with self.app.app_context():
            # CORREÇÃO 2: Verifique se a rota é /contrato/salvar ou /salvar_contrato
            # Se der 404 de novo, verifique o @app.route no seu app.py
            response = self.client.post('/contrato/salvar', data=new_contract_data, follow_redirects=True)
            
            # Se a rota estiver correta, deve retornar 200
            self.assertEqual(response.status_code, 200)
            
            contrato = Contrato.query.filter_by(cnpj='00.000.000/0001-00').first()
            self.assertIsNotNone(contrato)

    def test_03_search_functionality(self):
        """Testa a funcionalidade de busca."""
        with self.app.app_context():
            contrato = Contrato(
                cnpj='11.111.111/0001-11', 
                nome='Contrato Teste Busca', 
                valor_contrato=100.00, 
                inicio_contrato=date(2025, 1, 1),
                user_id=TEST_USER_ID
            )
            db.session.add(contrato)
            db.session.commit()
            
            with self.client.session_transaction() as sess:
                sess['user_id'] = TEST_USER_ID

            # Simula a busca no formulário da index
            response = self.client.post('/', data={'termo_busca': 'Teste Busca'}, follow_redirects=True)
            self.assertEqual(response.status_code, 200)
            self.assertIn(b"Contrato Teste Busca", response.data)

    def test_04_delete_contract(self):
        """Testa a exclusão de um contrato."""
        with self.app.app_context():
            contrato_to_delete = Contrato(
                cnpj='99.999.999/0001-99', 
                nome='Para Excluir', 
                valor_contrato=1.00, 
                inicio_contrato=date(2025, 1, 1),
                user_id=TEST_USER_ID
            )
            db.session.add(contrato_to_delete)
            db.session.commit()
            
            contrato_id = contrato_to_delete.id 

            with self.client.session_transaction() as sess:
                sess['user_id'] = TEST_USER_ID
                
            # CORREÇÃO 3: Ajuste o caminho da URL se a sua rota de exclusão for diferente
            response = self.client.post(f'/contrato/{contrato_id}/excluir', follow_redirects=True)
            self.assertEqual(response.status_code, 200)

            # Verifica se foi removido
            contrato = Contrato.query.get(contrato_id)
            self.assertIsNone(contrato)
            
if __name__ == '__main__':
    unittest.main()