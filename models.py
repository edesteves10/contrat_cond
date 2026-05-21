from extensions import db, login_manager
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy import Numeric 
from datetime import datetime # 🌟 IMPORTAÇÃO ADICIONADA


# Modelo de Usuário para autenticação Flask-Login
class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    
    # Relação com Contratos
    contratos = db.relationship('ContratCond', backref='usuario', lazy=True)

    def set_password(self, password):
        """Cria o hash da senha."""
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        """Verifica se a senha fornecida corresponde ao hash."""
        return check_password_hash(self.password_hash, password)

    def __repr__(self):
        return f"User('{self.username}')"

# Modelo de Contrato Condominial com todos os campos necessários
class Contrato(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    
    # Dados do Contratante
    nome = db.Column(db.String(200), nullable=False)
    cnpj = db.Column(db.String(18), unique=True, nullable=False)
    endereco = db.Column(db.String(300), nullable=False)
    cep = db.Column(db.String(10), nullable=False)
    estado = db.Column(db.String(2), nullable=False)
    telefone = db.Column(db.String(20), nullable=False)
    email = db.Column(db.String(100), nullable=False)
    
    # Dados do Contrato
    valor_contrato = db.Column(db.String(20), nullable=False) 
    inicio_contrato = db.Column(db.Date, nullable=False)
    termino_contrato = db.Column(db.Date, nullable=True) 
    abrangencia_contrato = db.Column(db.String(100), nullable=True)
    tipo_indice = db.Column(db.String(50), nullable=True)

    # Chave Estrangeira
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    
    # Coluna de data corrigida
    data_criacao = db.Column(db.DateTime, default=datetime.utcnow) 
    
    def __repr__(self):
        return f"Contrato('{self.nome}', '{self.cnpj}')"
