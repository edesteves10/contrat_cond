import os
import io
from io import BytesIO
import re
import requests
from decimal import Decimal
from datetime import datetime
import sqlite3
from flask import Flask, render_template, request, redirect, url_for, send_file, flash, session, jsonify, make_response
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from flask_wtf import FlaskForm
from flask_migrate import Migrate # Certifique-se de que está importado
from wtforms import StringField, DateField, DecimalField, SelectField, SubmitField, EmailField, PasswordField, TextAreaField
from wtforms.validators import DataRequired, Length, Regexp, Optional, Email, EqualTo, ValidationError

# ReportLab e PIL
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib.units import inch, cm
from PIL import Image as PIL_Image
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.platypus import Paragraph, Spacer, Image
from reportlab.lib.fonts import addMapping
from reportlab.platypus import SimpleDocTemplate # Necessário para a segunda função PDF (que foi removida)

# --- FUNÇÃO AUXILIAR PARA LIMPAR CNPJ ---
def clean_cnpj(cnpj_str):
    """Remove caracteres não numéricos de uma string."""
    if not cnpj_str:
        return ""
    # Usa regex para manter apenas dígitos (0-9)
    return re.sub(r'\D', '', cnpj_str)

# Definição do Rodapé
RODAPE_TEXTO = "Rua: GIOVANNI DI BALDUCCIO, 402 - VILA MORAES, SAO PAULO - São Paulo - SP - CEP: 04170-000 | Tel: 11999441135"

# --- FUNÇÕES DE UTILIDADE ---

def clean_currency(value_str):
    """Converte string formatada em moeda brasileira (R$ 1.234,56) para Decimal."""
    if not isinstance(value_str, str):
        value_str = str(value_str)
    # Remove R$, espaços, pontos de milhar e troca vírgula decimal por ponto.
    cleaned = re.sub(r'[R$\s.]', '', value_str).replace(',', '.')
    try:
        if not cleaned:
            return Decimal('0.00')
        return Decimal(cleaned)
    except Exception:
        return Decimal('0.00')

def format_currency_br(value):
    """Formata Decimal ou float para string em formato moeda brasileira (1.234,56)."""
    if value is None:
        return ""
    # Assume que o valor é float ou Decimal
    return "R$ {:,.2f}".format(value).replace(",", "X").replace(".", ",").replace("X", ".")


# --- CONFIGURAÇÃO DA APLICAÇÃO E BANCO DE DADOS ---
project_dir = os.path.dirname(os.path.abspath(__file__))
database_file = "sqlite:///{}".format(os.path.join(project_dir, "database.db"))

app = Flask(__name__)
app.config['SECRET_KEY'] = 'sua-chave-secreta-forte'
app.config['SQLALCHEMY_DATABASE_URI'] = database_file
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message_category = 'info'
login_manager.login_message = "Por favor, faça login para acessar esta página."


# --- MODELOS DO BANCO DE DADOS ---

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=True) # Alterado para nullable=True para simplificar
    password_hash = db.Column(db.String(256), nullable=False) # CORREÇÃO: Removida a duplicação

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

@login_manager.user_loader
def load_user(user_id):
    try:
        return User.query.get(int(user_id))
    except ValueError:
        return None

class ContratCond(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False)
    cnpj = db.Column(db.String(20), unique=True, nullable=False)
    endereco = db.Column(db.String(200), nullable=False)
    cep = db.Column(db.String(10), nullable=False)
    estado = db.Column(db.String(50), nullable=False)
    telefone = db.Column(db.String(20), nullable=False)
    email = db.Column(db.String(120), nullable=False)
    # DECIMAL para armazenar valores monetários com precisão
    valor_contrato = db.Column(db.Numeric(10, 2), nullable=False) 
    inicio_contrato = db.Column(db.Date, nullable=False)
    termino_contrato = db.Column(db.Date, nullable=True)
    abrangencia_contrato = db.Column(db.String(100), nullable=False)
    tipo_indice = db.Column(db.String(50), nullable=True)
    # Novo campo adicionado na parte 1
    clausulas_adicionais = db.Column(db.Text, nullable=True) 
    data_criacao = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    def __repr__(self):
        return f'<ContratCond {self.nome}>'


# --- FORMULÁRIOS (FLASK-WTF) ---

class LoginForm(FlaskForm):
    # CORREÇÃO: Usa 'username' para bater com o modelo e a lógica de busca
    username = StringField('Usuário', validators=[DataRequired()]) 
    password = PasswordField('Senha', validators=[DataRequired()])
    submit = SubmitField('Entrar')

class RegistrationForm(FlaskForm):
    username = StringField('Nome de Usuário', validators=[DataRequired(), Length(min=4, max=100)])
    password = PasswordField('Senha', validators=[DataRequired(), Length(min=6)])
    confirm_password = PasswordField('Confirmar Senha', validators=[DataRequired(), EqualTo('password', message='As senhas devem ser iguais.')])
    submit = SubmitField('Registrar')

# CLASSE UNIFICADA E CORRIGIDA: ContratoForm
class ContratoForm(FlaskForm):
    # CRÍTICO: Adiciona __init__ para aceitar o ID do contrato na edição
    def __init__(self, *args, contrato_id=None, **kwargs):
        super(ContratoForm, self).__init__(*args, **kwargs)
        self.contrato_id = contrato_id # Armazena o ID para uso na validação

    nome = StringField('Razão Social', validators=[DataRequired(), Length(max=100)])
    
    cnpj = StringField('CNPJ', validators=[
        DataRequired(),
        Length(min=18, max=18, message="CNPJ deve ter 14 dígitos e estar formatado (XX.XXX.XXX/XXXX-XX)."),
        Regexp(r'^\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2}$', message="Formato do CNPJ inválido.")
    ])
    
    # Usa StringField para permitir a formatação R$ 1.234,56 e aplica a limpeza como filtro
    valor_contrato = StringField(
        'Valor do Contrato (R$)', 
        validators=[DataRequired()],
        filters=[clean_currency] # Aplica a limpeza e conversão para Decimal antes da validação
    )
    
    # Mapeado para ContratCond.tipo_indice
    tipo_indice = SelectField('Índice de Reajuste', choices=[
        ('IPCA', 'IPCA (Índice Nacional de Preços ao Consumidor Amplo)'),
        ('IGP-M', 'IGP-M (Índice Geral de Preços - Mercado)'),
        ('INPC', 'INPC (Índice Nacional de Preços ao Consumidor)'),
        ('Outro', 'Outro / Fixo'),
    ], validators=[DataRequired()])
    
    inicio_contrato = DateField('Início do Contrato', format='%Y-%m-%d', validators=[DataRequired()])
    termino_contrato = DateField('Término do Contrato', format='%Y-%m-%d', validators=[Optional()])
    abrangencia_contrato = StringField('Abrangência', validators=[DataRequired(), Length(max=200)])
    
    estado = StringField('Estado (UF)', validators=[DataRequired(), Length(min=2, max=2)])
    cep = StringField('CEP', validators=[
        DataRequired(), 
        Length(min=9, max=9, message="CEP deve ter 8 dígitos e estar formatado (00000-000)."),
        Regexp(r'^\d{5}-\d{3}$', message="Formato do CEP inválido.")
    ])
    endereco = StringField('Endereço', validators=[DataRequired(), Length(max=200)])
    
    telefone = StringField('Telefone', validators=[
        DataRequired(), 
        Length(min=10, max=15, message="Telefone inválido."), 
        Regexp(r'^\(\d{2}\)\s\d{4,5}-\d{4}$', message="Formato de telefone inválido. Use (XX) XXXX-XXXX ou (XX) XXXXX-XXXX.")
    ])
    email = EmailField('E-mail', validators=[DataRequired(), Email(), Length(max=120)])
    
    clausulas_adicionais = TextAreaField('Cláusulas Adicionais', validators=[Optional()])

    submit = SubmitField('Salvar Contrato')

    # Validador de CNPJ (garante unicidade, exceto no contrato atual durante edição)
    def validate_cnpj(self, cnpj):
        cleaned_cnpj = cnpj.data
        # Usa ContratCond, o modelo correto
        query = ContratCond.query.filter_by(cnpj=cleaned_cnpj) 
        
        if self.contrato_id is not None:
            # Exclui o contrato atual da checagem para permitir a edição
            query = query.filter(ContratCond.id != self.contrato_id)
        
        contrato = query.first()
        if contrato:
            raise ValidationError('Este CNPJ já está cadastrado.')
        
        # Adicione esta classe junto com suas outras classes de formulário (LoginForm, RegistrationForm, ContratoForm)
class SearchForm(FlaskForm):
    # O campo usado para a pesquisa, que o template estava chamando de 'termo'
    termo = StringField('Pesquisar', validators=[Optional(), Length(max=100)])
    submit = SubmitField('Buscar')

# --- INICIALIZAÇÃO DO BANCO E CRIAÇÃO DE USUÁRIO ---

with app.app_context():
    try:
        db.create_all()
        print("Tabelas criadas com sucesso (se não existirem).")
        # Cria usuário admin (se não existir)
        if not User.query.filter_by(username='admin').first():
            admin_user = User(username='admin', email='admin@example.com') # Adicionei um email
            admin_user.set_password('admin')
            db.session.add(admin_user)
            db.session.commit()
            print("Usuário 'admin' (senha: 'admin') criado.")
    except Exception as e:
        print(f"Erro ao criar tabelas ou usuário admin: {e}")


# --- ROTAS DE AUTENTICAÇÃO ---

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
        
    form = LoginForm()
    if form.validate_on_submit():
        # CORREÇÃO: Busca por 'username'
        user = User.query.filter_by(username=form.username.data).first()
        
        # CORREÇÃO: Chama 'user.check_password(form.password.data)'
        if user and user.check_password(form.password.data):
            login_user(user)
            next_page = request.args.get('next')
            return redirect(next_page or url_for('index'))
        else:
            flash('Usuário ou senha incorretos.', 'danger')
            
    return render_template('login.html', form=form) # Passa o form para o template


@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Você foi desconectado.', 'info')
    return redirect(url_for('login'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    form = RegistrationForm() # Usa o formulário WTForms
    if form.validate_on_submit():
        try:
            # Verifica se o usuário já existe
            if User.query.filter_by(username=form.username.data).first():
                flash('Este nome de usuário já está em uso.', 'warning')
                return render_template('registro.html', form=form)

            new_user = User(username=form.username.data)
            new_user.set_password(form.password.data)
            
            db.session.add(new_user)
            db.session.commit()
            flash('Usuário registrado com sucesso! Faça login.', 'success')
            return redirect(url_for('login'))
        except Exception as e:
            db.session.rollback()
            flash(f'Erro ao registrar usuário: {e}', 'danger')
            
    return render_template('register.html', form=form)


# --- ROTAS DE CONTRATOS (CRUD e Pesquisa) ---

@app.route('/', methods=['GET', 'POST'])
# @login_required # Mantendo o seu decorator
def index():
    # 1. INSTANCIAÇÃO DE FORMULÁRIOS E VARIÁVEIS DE ESTADO
    form = ContratoForm()
    search_form = SearchForm() 
    
    search_query = request.args.get('termo', '')
    
    # Parâmetros de Paginação
    page = request.args.get('page', 1, type=int)
    per_page = 10 

    # --- LÓGICA POST (Adicionar Contrato) ---
    if form.validate_on_submit():
        try:
            valor_contrato_decimal = form.valor_contrato.data 
            
            # ... (Lógica de adição de novo contrato omitida para brevidade) ...
            novo_contrato = ContratCond(
                nome=form.nome.data, 
                cnpj=form.cnpj.data, # CNPJ deve ser armazenado limpo/mascarado conforme sua definição de modelo
                endereco=form.endereco.data, 
                cep=form.cep.data, 
                estado=form.estado.data,
                telefone=form.telefone.data, 
                email=form.email.data, 
                tipo_indice=form.tipo_indice.data, 
                valor_contrato=valor_contrato_decimal, 
                inicio_contrato=form.inicio_contrato.data,
                termino_contrato=form.termino_contrato.data, 
                abrangencia_contrato=form.abrangencia_contrato.data,
                clausulas_adicionais=form.clausulas_adicionais.data
            )
            db.session.add(novo_contrato)
            db.session.commit()
            flash('Contrato adicionado com sucesso!', 'success')
            return redirect(url_for('index'))
        except Exception as e:
            db.session.rollback()
            flash(f'Erro ao adicionar contrato: {e}', 'danger')
            return redirect(url_for('index'))
            
    # --- LÓGICA GET (Pesquisa e Paginação) ---
    
    # 1. Inicia a query com a ordenação padrão
    query = ContratCond.query.order_by(ContratCond.data_criacao.desc())

    # 2. Se houver um termo de busca, aplica o filtro
    if search_query:
        # Padrão de busca para Nome/Endereço (usa o termo bruto)
        search_pattern = f"%{search_query}%"
        
        # Padrão de busca para CNPJ (limpa o termo e busca apenas números)
        cleaned_search_query = clean_cnpj(search_query)
        cleaned_search_pattern = f"%{cleaned_search_query}%"
        
        # Filtra a query EXISTENTE, aplicando a lógica OR
        query = query.filter(
            # Busca em Nome e Endereço (permite busca por partes)
            (ContratCond.nome.ilike(search_pattern)) | 
            (ContratCond.endereco.ilike(search_pattern)) |
            
            # Busca em CNPJ:
            # Opção A: Busca usando o termo LIMPO (assume que CNPJ no DB é numérico)
            (ContratCond.cnpj.ilike(cleaned_search_pattern)) | 
            # Opção B: Mantém busca com termo BRUTO (caso algum CNPJ esteja mascarado no DB)
            (ContratCond.cnpj.ilike(search_pattern)) 
        )
        
        # Opcionalmente, se você quiser garantir que o formulário de busca mantenha o valor
        search_form.termo.data = search_query
        
    # 3. Executa a paginação na query FINAL (filtrada ou não filtrada)
    contratos = query.paginate(page=page, per_page=per_page, error_out=False)

    # 2. RENDERIZAÇÃO DO TEMPLATE
    return render_template('index.html', 
                            form=form,
                            search_form=search_form, 
                            contratos=contratos, 
                            search_query=search_query)

# ... (O restante do seu código, rotas de edição, exclusão, etc.)


@app.route('/contrato/<int:contrato_id>/editar', methods=['GET', 'POST'])
@login_required
def editar_contrato(contrato_id):
    # Usa o nome do modelo correto: ContratCond
    contrato = ContratCond.query.get_or_404(contrato_id)
    
    # 1. PASSO CRÍTICO: Passar o ID do contrato para o formulário
    # Isso permite que a função validate_cnpj saiba que o CNPJ atual é permitido.
    form = ContratoForm(contrato_id=contrato.id) 
    
    if form.validate_on_submit():
        try:
            # Aplica a atualização dos campos
            contrato.nome = form.nome.data
            contrato.cnpj = form.cnpj.data
            contrato.endereco = form.endereco.data
            contrato.cep = form.cep.data
            contrato.estado = form.estado.data
            contrato.telefone = form.telefone.data
            contrato.email = form.email.data
            # O filtro já converteu form.valor_contrato.data para Decimal
            contrato.valor_contrato = form.valor_contrato.data 
            contrato.inicio_contrato = form.inicio_contrato.data
            contrato.termino_contrato = form.termino_contrato.data
            contrato.abrangencia_contrato = form.abrangencia_contrato.data
            contrato.tipo_indice = form.tipo_indice.data
            contrato.clausulas_adicionais = form.clausulas_adicionais.data
            
            db.session.commit()
            flash('Contrato atualizado com sucesso!', 'success')
            return redirect(url_for('index'))
        except Exception as e:
            db.session.rollback()
            flash(f'Erro ao atualizar contrato: {e}', 'danger')
            
    elif request.method == 'GET':
        # Ao carregar a página (GET), preencha o formulário
        form.nome.data = contrato.nome
        form.cnpj.data = contrato.cnpj
        form.endereco.data = contrato.endereco
        form.cep.data = contrato.cep
        form.estado.data = contrato.estado
        form.telefone.data = contrato.telefone
        form.email.data = contrato.email
        form.tipo_indice.data = contrato.tipo_indice
        form.inicio_contrato.data = contrato.inicio_contrato
        form.termino_contrato.data = contrato.termino_contrato
        form.abrangencia_contrato.data = contrato.abrangencia_contrato
        form.clausulas_adicionais.data = contrato.clausulas_adicionais

        # CRÍTICO: Formata o valor Decimal para string com o formato brasileiro
        form.valor_contrato.data = format_currency_br(contrato.valor_contrato)
            
    return render_template('editar.html', form=form, contrato=contrato)

@app.route('/delete/<int:id>', methods=['POST'])
@login_required
def delete_contrato(id):
    contrato = ContratCond.query.get_or_404(id)
    try:
        db.session.delete(contrato)
        db.session.commit()
        flash('Contrato excluído com sucesso!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Erro ao excluir contrato: {e}', 'danger')
    return redirect(url_for('index'))


@app.route('/clausulas')
@login_required
def clausulas():
    # As cláusulas foram mantidas no Python, mas o ideal seria em um template ou no DB.
    clausulas_contrato = """
    <h2>Cláusulas Gerais do Contrato</h2>
    ... (Conteúdo das cláusulas) ...
    """
    # Usando o HTML do seu código original para retorno
    return render_template('clausulas.html', clausulas=clausulas_contrato)


# --- ROTAS DE API ---

@app.route("/api/cnpj/<cnpj>")
@login_required # Protege a API
def buscar_cnpj(cnpj):
    # Remove caracteres não numéricos do CNPJ antes de buscar
    cnpj_limpo = re.sub(r'[^0-9]', '', cnpj)
    try:
        # Requer a instalação da biblioteca 'requests'
        r = requests.get(f"https://receitaws.com.br/v1/cnpj/{cnpj_limpo}")
        r.raise_for_status() # Lança exceção para códigos de erro HTTP
        data = r.json()
        return jsonify(data)
    except requests.exceptions.HTTPError as he:
        # Trata erros específicos da API da ReceitaWS
        return jsonify({"status": "ERROR", "message": f"Erro HTTP ao buscar CNPJ: {he.response.status_code}"}), 400
    except Exception as e:
        return jsonify({"status": "ERROR", "message": str(e)}), 500


# --- ROTA DE GERAÇÃO DE PDF (Unificada e Corrigida) ---

# Rota mantida com o nome da Parte 2 (a mais completa)
@app.route('/download_contrato_pdf/<int:id>')
@login_required
def download_contrato_pdf(id):
    # Usa o modelo correto para buscar o contrato real
    contrato = ContratCond.query.get_or_404(id)

    try:
        output = io.BytesIO()
        
        # === CONFIGURAÇÃO DE REPORTLAB ===
        margem_superior = 2 * cm
        margem_inferior = 2 * cm
        margem_esquerda = 2 * cm
        margem_direita = 2 * cm
        page_width, page_height = letter

        p = canvas.Canvas(output, pagesize=letter)
        styles = getSampleStyleSheet()
        
        # Definição de estilos
        normal_style = ParagraphStyle(name='Normal', fontName='Helvetica', fontSize=10, leading=14, alignment=TA_LEFT)
        bold_style = ParagraphStyle(name='BoldStyle', parent=normal_style, fontName='Helvetica-Bold')
        centered_style = ParagraphStyle(name='Centered', parent=normal_style, alignment=TA_CENTER)
        
        # Estilos específicos
        # MUDANÇA 1: Fonte do cabeçalho mantida em 12pt
        header_style = ParagraphStyle(name='HeaderInfo', parent=normal_style, fontSize=12, leading=14, spaceAfter=0.1 * cm)
        # MUDANÇA 2: Espaçamento após o título mantido em 0.5 cm
        title_style = ParagraphStyle(name='ContractTitle', fontName='Helvetica-Bold', fontSize=15, leading=18, alignment=TA_CENTER, spaceAfter=0.5 * cm)
        right_aligned_style = ParagraphStyle(name='RightAligned', parent=normal_style, alignment=TA_RIGHT, fontSize=10, spaceAfter=0.5 * cm)
        clausula_style = ParagraphStyle(name='Clausula', parent=normal_style, fontSize=11, leading=16, spaceAfter=0.5 * cm)
        signature_label_style = ParagraphStyle(name='SignatureLabel', parent=centered_style, fontSize=10, leading=12)
        footer_style = ParagraphStyle(name='Footer', parent=normal_style, fontName='Helvetica', fontSize=8, alignment=TA_CENTER)
        
        current_y = page_height - margem_superior
        content_width = page_width - margem_esquerda - margem_direita
        
        # --- CABEÇALHO (Logo e Info da Empresa) ---
        logo_path = os.path.join(os.getcwd(), 'static', 'logo.png')
        logo_width = 3 * cm
        logo_height = 1.5 * cm

        # 1. Tenta desenhar o logo
        try:
            p.drawImage(logo_path, margem_esquerda, current_y - logo_height, width=logo_width, height=logo_height)
        except Exception as e:
            # Fallback (Desenha o texto M.A. Automação no lugar)
            fallback_para = Paragraph("M.A. Automação", bold_style)
            fallback_para.wrapOn(p, logo_width, page_height)
            fallback_para.drawOn(p, margem_esquerda, current_y - fallback_para.height)

        # 2. Informações da empresa ao lado do logo
        info_x = margem_esquerda + logo_width + 0.5 * cm
        info_width = content_width - logo_width - 0.5 * cm

        empresa_para = Paragraph("M.A. Automação", header_style)
        cnpj_para = Paragraph("CNPJ: 27.857.310/0001-83", header_style)

        # Desenha "M.A. Automação"
        empresa_para.wrapOn(p, info_width, page_height)
        empresa_para.drawOn(p, info_x, current_y - empresa_para.height)
        
        # Desenha CNPJ
        cnpj_para.wrapOn(p, info_width, page_height)
        cnpj_para.drawOn(p, info_x, current_y - empresa_para.height - cnpj_para.height)
        
        # Ajusta a altura atual após o cabeçalho (usa o elemento mais alto: o logo)
        current_y -= logo_height + 0.5 * cm
        
        # Linha separadora do cabeçalho
        p.line(margem_esquerda, current_y, page_width - margem_direita, current_y)
        current_y -= 0.5 * cm

        # --- TÍTULO DO CONTRATO ---
        title_para = Paragraph("CONTRATO DE PRESTAÇÃO DE SERVIÇOS", title_style)
        title_para.wrapOn(p, content_width, page_height)
        title_x = margem_esquerda + (content_width - title_para.width) / 2
        title_para.drawOn(p, title_x, current_y - title_para.height)
        current_y -= title_para.height
        
        # Espaçamento entre o título e a data
        current_y -= 0.5 * cm 

        # --- LOCAL E DATA ---
        data_atual = datetime.now()
        meses = {1: 'janeiro', 2: 'fevereiro', 3: 'março', 4: 'abril', 5: 'maio', 6: 'junho', 7: 'julho', 8: 'agosto', 9: 'setembro', 10: 'outubro', 11: 'novembro', 12: 'dezembro'}
        data_formatada = f"São Paulo, {data_atual.day} de {meses.get(data_atual.month, '')} de {data_atual.year}"
        local_data_para = Paragraph(data_formatada, right_aligned_style)
        
        local_data_para.wrapOn(p, content_width, page_height)
        local_data_x = page_width - margem_direita - local_data_para.width # Alinha à direita
        local_data_para.drawOn(p, local_data_x, current_y - local_data_para.height) 
        current_y -= local_data_para.height 
        
        # MUDANÇA 1: Aumenta o espaçamento após a data (entre a data e o bloco de detalhes)
        current_y -= 1.0 * cm 

        # --- DADOS DO CONTRATO (2 COLUNAS) ---
        
        # Definindo colunas e suas larguras
        col_labels_width = 3.5 * cm
        col_values_width = 6 * cm
        
        col1_x = margem_esquerda
        col2_x = margem_esquerda + col_labels_width + col_values_width
        
        # Definindo os dados em pares de [Chave, Valor]
        contrato_details_pairs = [
            # Coluna 1
            [('Nome:', contrato.nome), ('CNPJ:', contrato.cnpj), ('Telefone:', contrato.telefone), ('Email:', contrato.email), ('Valor do Contrato:', format_currency_br(contrato.valor_contrato)), ('Início do Contrato:', contrato.inicio_contrato.strftime('%d de %B de %Y') if contrato.inicio_contrato else 'Não definido')],
            # Coluna 2
            [('Término do Contrato:', contrato.termino_contrato.strftime('%d de %B de %Y') if contrato.termino_contrato else 'Não definido'), ('Abrangência do Contrato:', contrato.abrangencia_contrato), ('Tipo de Índice de Reajuste:', contrato.tipo_indice), ('Endereço Completo:', f"{contrato.endereco}, {contrato.cep}, {contrato.estado}")]
        ]

        # Ajuste vertical para o layout de duas colunas
        start_y = current_y

        # Processa Coluna 1 (primeiro elemento de cada par)
        col1_y = start_y
        for label, value in contrato_details_pairs[0]:
            label_para = Paragraph(f"<b>{label}</b>", normal_style)
            value_para = Paragraph(str(value), normal_style)
            
            # Desenha Label (esquerda)
            label_para.wrapOn(p, col_labels_width, page_height)
            label_para.drawOn(p, col1_x, col1_y - label_para.height)
            
            # Desenha Valor (direita da Coluna 1)
            value_para.wrapOn(p, col_values_width, page_height)
            value_para.drawOn(p, col1_x + col_labels_width, col1_y - value_para.height)
            
            # Atualiza Y
            col1_y -= max(label_para.height, value_para.height) + 0.2 * cm
            
        # Processa Coluna 2 (segundo elemento de cada par)
        col2_y = start_y
        for label, value in contrato_details_pairs[1]:
            label_para = Paragraph(f"<b>{label}</b>", normal_style)
            value_para = Paragraph(str(value), normal_style)
            
            # Desenha Label (esquerda)
            label_para.wrapOn(p, col_labels_width, page_height)
            label_para.drawOn(p, col2_x, col2_y - label_para.height)
            
            # Desenha Valor (direita da Coluna 2)
            value_para.wrapOn(p, col_values_width, page_height)
            value_para.drawOn(p, col2_x + col_labels_width, col2_y - value_para.height)
            
            # Atualiza Y
            col2_y -= max(label_para.height, value_para.height) + 0.2 * cm

        # O novo Y atual deve ser o menor entre col1_y e col2_y
        current_y = min(col1_y, col2_y) - 0.5 * cm 

        # --- CLÁUSULA PRIMEIRA ---
        # Título da Cláusula
        clausula_title_para = Paragraph("<u>CLÁUSULA PRIMEIRA - DO OBJETO</u>", bold_style)
        clausula_title_para.wrapOn(p, content_width, page_height)
        clausula_title_para.drawOn(p, margem_esquerda, current_y - clausula_title_para.height)
        current_y -= clausula_title_para.height + 0.2 * cm

        # Texto da Cláusula (Adaptado para contrato)
        clausula_objeto_text = f"""
        Pelo presente instrumento, as partes acima qualificadas, de comum acordo, 
        ajustam a prestação dos serviços de {contrato.abrangencia_contrato or ' [ÁREA DE SERVIÇO] '}, 
        mediante as especificações e condições estabelecidas neste documento, com início em 
        {contrato.inicio_contrato.strftime('%d/%m/%Y') if contrato.inicio_contrato else ' [DATA INICIAL] '} 
        e término em 
        {contrato.termino_contrato.strftime('%d/%m/%Y') if contrato.termino_contrato else ' [DATA FINAL] '}, 
        com o valor total de {format_currency_br(contrato.valor_contrato)}.
        """
        clausula_para = Paragraph(clausula_objeto_text, clausula_style)
        clausula_para.wrapOn(p, content_width, page_height)
        clausula_para.drawOn(p, margem_esquerda, current_y - clausula_para.height)
        current_y -= clausula_para.height + 0.5 * cm
        
        # Cláusulas Adicionais (Se houverem)
        if contrato.clausulas_adicionais:
            clausula_adicional_title = Paragraph("<u>CLÁUSULAS ADICIONAIS</u>", bold_style)
            clausula_adicional_title.wrapOn(p, content_width, page_height)
            clausula_adicional_title.drawOn(p, margem_esquerda, current_y - clausula_adicional_title.height)
            current_y -= clausula_adicional_title.height + 0.2 * cm
            
            clausulas_adicionais_para = Paragraph(contrato.clausulas_adicionais, clausula_style)
            clausulas_adicionais_para.wrapOn(p, content_width, page_height)
            clausulas_adicionais_para.drawOn(p, margem_esquerda, current_y - clausulas_adicionais_para.height)
            current_y -= clausulas_adicionais_para.height + 0.5 * cm
            
            # Se houverem cláusulas adicionais, adiciona um espaço maior antes do aceite
            space_after_clausulas = 2.0 * cm 
        else:
            # Caso contrário, um espaço menor
            space_after_clausulas = 1.5 * cm

        # --- TEXTO DE ACEITE (Li e concordo...) ---
        
        # Define o ponto mínimo onde a frase de aceite deve começar (3 cm acima da linha de assinatura, deixando 1cm para a frase e 0.5cm de margem)
        y_line_position_signature = margem_inferior + 3 * cm
        y_assinaturas_min = y_line_position_signature + 1.5 * cm # 1.5 cm acima da linha de assinatura

        # MUDANÇA 2: Calcula a posição Y da frase de aceite
        # Posição calculada com base no fim da última cláusula + espaçamento
        y_calculated_for_aceite = current_y - space_after_clausulas 
        
        # Usa a posição calculada, mas garante que não seja menor que o mínimo
        final_y_aceite = max(y_calculated_for_aceite, y_assinaturas_min)
             
        # Texto e Estilo
        aceite_text = "Li e concordo com os termos do contrato."
        aceite_style = ParagraphStyle(name='Aceite', parent=centered_style, fontName='Helvetica', fontSize=10, leading=12)

        aceite_para = Paragraph(aceite_text, aceite_style)
        aceite_para.wrapOn(p, content_width, page_height)

        # Desenha o texto de aceite no Y ajustado
        aceite_x = margem_esquerda + (content_width - aceite_para.width) / 2
        aceite_para.drawOn(p, aceite_x, final_y_aceite - aceite_para.height)
        
        # Atualiza current_y para a próxima seção
        current_y = final_y_aceite - aceite_para.height - 0.5 * cm

        # --- ASSINATURAS (Posicionamento Fixo) ---
        
        signature_line_length = 6 * cm 
        
        # Assinatura Empresa (Esquerda)
        x_empresa_center = margem_esquerda + (content_width / 4)
        x_empresa_line_start = x_empresa_center - (signature_line_length / 2)
        
        p.line(x_empresa_line_start, y_line_position_signature, x_empresa_line_start + signature_line_length, y_line_position_signature)
        
        empresa_label_para = Paragraph("Assinatura Empresa (M.A. Automação)", signature_label_style)
        empresa_label_para.wrapOn(p, signature_line_length, page_height)
        empresa_label_y = y_line_position_signature - empresa_label_para.height - 0.2 * cm
        empresa_label_para.drawOn(p, x_empresa_line_start, empresa_label_y)

        # Assinatura Contratante (Direita)
        x_contratante_center = margem_esquerda + (content_width * 3 / 4)
        x_contratante_line_start = x_contratante_center - (signature_line_length / 2)
        
        p.line(x_contratante_line_start, y_line_position_signature, x_contratante_line_start + signature_line_length, y_line_position_signature)
        
        contratante_nome_para = Paragraph(contrato.nome.upper(), signature_label_style)
        contratante_nome_para.wrapOn(p, signature_line_length, page_height)
        contratante_nome_y = y_line_position_signature - contratante_nome_para.height - 0.2 * cm
        contratante_nome_para.drawOn(p, x_contratante_line_start, contratante_nome_y)

        contratante_label_para = Paragraph("Assinatura Contratante", signature_label_style)
        contratante_label_para.wrapOn(p, signature_line_length, page_height)
        contratante_label_y = contratante_nome_y - contratante_label_para.height - 0.2 * cm 
        contratante_label_para.drawOn(p, x_contratante_line_start, contratante_label_y)

        # --- RODAPÉ (Fixo) ---
        footer_para = Paragraph(RODAPE_TEXTO, footer_style)
        footer_para.wrapOn(p, content_width, page_height)
        footer_x_center = margem_esquerda + (content_width - footer_para.width) / 2 
        footer_para.drawOn(p, footer_x_center, margem_inferior - (0.5 * cm) ) 

        # === FIM DA LÓGICA DO PDF ===

        p.save()

        output.seek(0)
        filename = f"contrato_{contrato.nome.replace(' ', '_').replace('.', '').replace('/', '')}.pdf"
        return send_file(output, as_attachment=True, download_name=filename, mimetype='application/pdf')

    except Exception as e:
        # Aumentei o nível de detalhes para debugging em caso de erro.
        flash(f'Erro ao gerar o PDF: {e}', 'danger')
        print(f'Erro ao gerar o PDF: {e}')
        # print(f"Erro detalhado ao carregar logo: {os.path.join(os.getcwd(), 'static', 'logo.png')}") 
        return redirect(url_for('index'))
    
    # --- FUNÇÕES DE UTILIDADE (Continuação) ---
# ... (sua função format_currency_br está aqui)

# --- REGISTRO DO FILTRO JINJA ---
with app.app_context():
    # Registra a função Python 'format_currency_br' para que seja acessível
    # nos templates HTML como o filtro 'currency_br'
    app.jinja_env.filters['currency_br'] = format_currency_br

# --- ROTAS DE AUTENTICAÇÃO --- 
# ... (restante do código)


if __name__ == '__main__':
    # Para rodar localmente, o 'requests' é usado no /api/cnpj/<cnpj>
    app.run(debug=True)