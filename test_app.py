import unittest
from app import app as flask_app, db, User # Importe seu modelo User se existir
from app import ContratCond as Contrato 
from datetime import date
from flask_login import login_user

class ContractAppTestCase(unittest.TestCase):

    def setUp(self):
        self.app = flask_app
        self.app.config['TESTING'] = True
        self.app.config['WTF_CSRF_ENABLED'] = False 
        self.app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:' 
        # A linha abaixo desativa o @login_required apenas para os testes
        self.app.config['LOGIN_DISABLED'] = True 
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
            'telefone': '(11) 99999-9999',
            'email': 'teste@teste.com',
            'valor_contrato': '5000,00', 
            'inicio_contrato': '2025-01-01',
            'termino_contrato': '2026-01-01',
            'abrangencia_contrato': 'Total',
            'tipo_indice': 'IGP-M'
        }

        response = self.client.post('/', data=new_contract_data, follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        
        with self.app.app_context():
            contrato = Contrato.query.filter_by(nome='CONDOMINIO TESTE').first()
            self.assertIsNotNone(contrato)

    def test_03_search_functionality(self):
        """Testa a busca."""
        with self.app.app_context():
            c = Contrato(
                nome="BUSCA_TARGET", 
                cnpj="123", 
                endereco="Endereço Teste",
                cep="00000-000",
                estado="SP",
                telefone="1199999999",
                email="busca@teste.com",
                abrangencia_contrato="Total",
                valor_contrato=100.0, 
                inicio_contrato=date(2025,1,1)
            )
            db.session.add(c)
            db.session.commit()

            response = self.client.get('/?termo=BUSCA_TARGET')
            self.assertEqual(response.status_code, 200)
            self.assertIn(b"BUSCA_TARGET", response.data)

    def test_04_delete_contract(self):
        """Testa a exclusão de contrato (contornando @login_required)."""
        with self.app.app_context():
            c = Contrato(
                nome="DELETAR", 
                cnpj="456", 
                endereco="Endereço Teste",
                cep="00000-000",
                estado="SP",
                telefone="1199999999",
                email="delete@teste.com",
                abrangencia_contrato="Total",
                valor_contrato=100.0, 
                inicio_contrato=date(2025,1,1)
            )
            db.session.add(c)
            db.session.commit()
            contrato_id = c.id

        # Como LOGIN_DISABLED = True no setUp, o @login_required será ignorado aqui
        response = self.client.post(f'/delete/{contrato_id}', follow_redirects=True)
        self.assertEqual(response.status_code, 200)

        with self.app.app_context():
            # Usando db.session.get (v2.0+) para evitar o warning anterior
            contrato = db.session.get(Contrato, contrato_id)
            self.assertIsNone(contrato, "O contrato ainda existe. O @login_required pode estar bloqueando o teste.")

if __name__ == '__main__':
    unittest.main()