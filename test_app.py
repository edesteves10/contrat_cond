import unittest
from app import app as flask_app, db 
from app import ContratCond as Contrato 
from datetime import date

class ContractAppTestCase(unittest.TestCase):

    def setUp(self):
        self.app = flask_app
        self.app.config['TESTING'] = True
        self.app.config['WTF_CSRF_ENABLED'] = False 
        self.app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:' 
        self.client = self.app.test_client()

        with self.app.app_context():
            db.create_all()

    def tearDown(self):
        with self.app.app_context():
            db.session.remove()
            db.drop_all()

    def test_01_login_page_loads(self):
        """Verifica se a página de login carrega."""
        response = self.client.get('/login')
        self.assertEqual(response.status_code, 200)

    def test_02_contract_creation(self):
        """Testa o cadastro via formulário POST."""
        new_contract_data = {
            'cnpj': '00.000.000/0001-00',
            'nome': 'CONDOMINIO TESTE',
            'endereco': 'Rua de Teste, 123',
            'cep': '01000-000',
            'estado': 'SP',
            'valor_contrato': '5000,00', 
            'inicio_contrato': '2025-01-01',
            'termino_contrato': '2026-01-01',
            'email': 'teste@teste.com',
            'tipo_indice': 'IGP-M'
        }

        response = self.client.post('/', data=new_contract_data, follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        
        with self.app.app_context():
            contrato = Contrato.query.filter_by(nome='CONDOMINIO TESTE').first()
            self.assertIsNotNone(contrato, "O formulário falhou na validação. Verifique se há campos obrigatórios faltando no dict 'new_contract_data'.")

    def test_03_search_functionality(self):
        """Testa a busca garantindo que o objeto criado no banco tenha todos os campos NOT NULL."""
        with self.app.app_context():
            c = Contrato(
                nome="BUSCA_TARGET", 
                cnpj="123", 
                endereco="Endereço Teste",
                cep="00000-000",   # ADICIONADO
                estado="SP",        # ADICIONADO
                valor_contrato=100.0, 
                inicio_contrato=date(2025,1,1)
            )
            db.session.add(c)
            db.session.commit()

            response = self.client.get('/?termo=BUSCA_TARGET')
            self.assertEqual(response.status_code, 200)
            self.assertIn(b"BUSCA_TARGET", response.data)

    def test_04_delete_contract(self):
        """Testa a exclusão garantindo que o objeto criado tenha todos os campos NOT NULL."""
        with self.app.app_context():
            c = Contrato(
                nome="DELETAR", 
                cnpj="456", 
                endereco="Endereço Teste",
                cep="00000-000",   # ADICIONADO
                estado="SP",        # ADICIONADO
                valor_contrato=100.0, 
                inicio_contrato=date(2025,1,1)
            )
            db.session.add(c)
            db.session.commit()
            contrato_id = c.id

        response = self.client.post(f'/delete/{contrato_id}', follow_redirects=True)
        self.assertEqual(response.status_code, 200)

        with self.app.app_context():
            contrato = Contrato.query.get(contrato_id)
            self.assertIsNone(contrato)

if __name__ == '__main__':
    unittest.main()