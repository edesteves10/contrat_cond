import os
from flask import Flask, render_template, redirect, url_for, flash, request, make_response
from flask_sqlalchemy import SQLAlchemy
from flask_wtf.csrf import CSRFProtect
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from wtforms import StringField, PasswordField, SubmitField, DateField, SelectField, TextAreaField
from wtforms.validators import DataRequired, Length, Email, Regexp, Optional, ValidationError, EqualTo # <-- ADICIONE O 'EqualTo' AQUI
from wtforms.validators import DataRequired, Length, Email, Regexp, Optional, ValidationError
from flask_wtf import FlaskForm
from wtforms import HiddenField
from datetime import date
from flask_migrate import Migrate
from werkzeug.routing import BuildError # Para referência, se 
import locale
import re
import io # Necessário para gerar o PDF em memória (pdf_buffer)
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.enums import TA_JUSTIFY, TA_CENTER
from reportlab.lib import colors
import datetime # Importe o módulo completo (melhor prática para evitar conflitos)
from io import BytesIO
from flask import Flask, flash, redirect, url_for, send_file, request, jsonify, render_template
from pdf_generator import gerar_pdf_reportlab, limpar_valor_moeda
from datetime import date, datetime # Garanta que datetime e date estão importados
from datetime import date # Importe também a classe date para uso direto, se preferir
from models import Contrato
import decimal
from decimal import Decimal # Garanta que este import está lá
from wtforms import Form, StringField, validators, DecimalField
from wtforms.widgets import Input
# IMPORTAÇÃO CRÍTICA DO PDF
import locale
# Define o locale para português do Brasil (necessário para formatação de moeda)
# Use 'pt_BR.utf8' para Linux/macOS ou 'Portuguese_Brazil.1252' para Windows

class ExclusaoContratoForm(FlaskForm):
    # Um formulário simples que só carrega o CSRF token
    pass 


try:
    locale.setlocale(locale.LC_ALL, 'pt_BR.utf8')
except locale.Error:
    try:
        # Tenta um locale comum no Windows
        locale.setlocale(locale.LC_ALL, 'Portuguese_Brazil.1252')
    except locale.Error:
        print("Aviso: Locale 'pt_BR' não encontrado. Formatador de moeda pode não funcionar corretamente.")
        

    # ----------------------------------------------------------------------
# 1. FUNÇÃO DE GERAÇÃO DE PDF (DEVE SER DEFINIDA FORA DE QUALQUER ROTA)
# ----------------------------------------------------------------------

def generate_contract_pdf(data):
    """
    Gera um contrato em PDF usando os dados fornecidos.
    
    Args:
        data (dict): Dicionário contendo todos os dados do contrato, 
                     incluindo a string formatada 'contratante_completo'.
        
    Returns:
        io.BytesIO: Buffer com os bytes do PDF.
    """
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer, 
        pagesize=A4,
        topMargin=50,
        bottomMargin=50,
        leftMargin=50,
        rightMargin=50
    )
    styles = getSampleStyleSheet()
    
    # Estilos customizados
    styles.add(ParagraphStyle(name='Justify', alignment=TA_JUSTIFY, fontSize=11, leading=14))
    styles.add(ParagraphStyle(name='Heading', alignment=TA_CENTER, fontSize=16, leading=20, spaceAfter=20))
    styles.add(ParagraphStyle(name='Subtitle', alignment=TA_CENTER, fontSize=12, leading=15, spaceAfter=15))
    styles.add(ParagraphStyle(name='Center', alignment=TA_CENTER, fontSize=11, leading=14))
    
    elements = []
    
    # Título do Documento
    elements.append(Paragraph("CONTRATO DE PRESTAÇÃO DE SERVIÇOS", styles['Heading']))
    elements.append(Paragraph("Referência: CNPJ " + data['cnpj'], styles['Subtitle']))
    elements.append(Spacer(1, 12))

    # Cláusula de Identificação das Partes
    elements.append(Paragraph("<b>CLÁUSULA PRIMEIRA: DAS PARTES CONTRATANTES</b>", styles['Justify']))
    elements.append(Spacer(1, 6))
    
    # AGORA USAMOS A CHAVE 'contratante_completo' QUE SERÁ MONTADA NO download_pdf
    # Isso evita a KeyError
    elements.append(Paragraph(data['contratante_completo'], styles['Justify']))
    
    # OBS: O CONTRATADO DEVE SER UMA VARIÁVEL FIXA (SUA EMPRESA).
    contratado = "<b>CONTRATADO:</b> [Nome da Sua Empresa/Condomínio], CNPJ [Seu CNPJ], com sede em [Seu Endereço]."
    elements.append(Paragraph(contratado, styles['Justify']))
    elements.append(Spacer(1, 12))

    # Cláusula do Objeto e Valor
    elements.append(Paragraph("<b>CLÁUSULA SEGUNDA: DO OBJETO E VALOR</b>", styles['Justify']))
    elements.append(Spacer(1, 6))
    
    elements.append(Paragraph(
        f"2.1. O objeto deste contrato é a prestação de serviços na abrangência de <b>{data['abrangencia_contrato']}</b>.", 
        styles['Justify']
    ))
    elements.append(Paragraph(
        f"2.2. O valor total acordado para o contrato é de <b>R$ {data['valor_contrato']}</b> (reais).", 
        styles['Justify']
    ))
    elements.append(Spacer(1, 12))

    # Cláusula da Duração
    elements.append(Paragraph("<b>CLÁUSULA TERCEIRA: DA DURAÇÃO E REAJUSTE</b>", styles['Justify']))
    elements.append(Spacer(1, 6))
    
    elements.append(Paragraph(
        f"3.1. Este contrato tem início em <b>{data['inicio_contrato']}</b> e término previsto para <b>{data['termino_contrato']}</b>.", 
        styles['Justify']
    ))
    elements.append(Paragraph(
        f"3.2. O índice de reajuste anual a ser aplicado é o <b>{data['tipo_indice']}</b>.", 
        styles['Justify']
    ))
    elements.append(Spacer(1, 12))
    
    # Cláusulas Adicionais (Campo Texto Livre)
    elements.append(Paragraph("<b>CLÁUSULA QUARTA: DISPOSIÇÕES FINAIS E ADICIONAIS</b>", styles['Justify']))
    elements.append(Spacer(1, 6))
    elements.append(Paragraph(
        f"4.1. As seguintes cláusulas adicionais fazem parte integrante deste instrumento:",
        styles['Justify']
    ))
    
    # Formatação do texto longo das cláusulas adicionais
    clausulas_ad_paragraph = Paragraph(data['clausulas_adicionais'].replace('\n', '<br/>'), styles['Justify'])
    elements.append(clausulas_ad_paragraph)
    elements.append(Spacer(1, 18))

    # Espaço para Assinaturas
    elements.append(Paragraph("E por estarem de acordo, as partes assinam o presente.", styles['Center']))
    elements.append(Spacer(1, 30))
    
    data_assinatura = [
        [Paragraph(f"__________________________________", styles['Center']), 
         Paragraph(f"__________________________________", styles['Center'])],
        # Usamos o nome que já existe
        [Paragraph(f"<b>{data['nome']}</b> (Contratante)", styles['Center']), 
         Paragraph(f"<b>[Nome do Contratado]</b>", styles['Center'])]
    ]
    
    t = Table(data_assinatura, colWidths=[doc.width/2.0]*2)
    t.setStyle(TableStyle([
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ('BOTTOMPADDING', (0,0), (-1,0), 0)
    ]))
    elements.append(t)
    
    # Monta o documento
    doc.build(elements)
    
    # Retorna o buffer para ser enviado pelo Flask
    buffer.seek(0)
    return buffer


# Configuração
app = Flask(__name__)
# Chave de segurança deve ser carregada de forma segura em produção
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'sua_chave_secreta_muito_segura')
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///contratos.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
csrf = CSRFProtect(app)
login_manager = LoginManager()
login_manager = LoginManager(app)
login_manager.login_view = 'login'
login_manager.init_app(app)
# Certifique-se de que isso é executado no contexto da aplicação

# INICIALIZAÇÃO DO FLASK-MIGRATE
migrate = Migrate(app, db)


# MOCK DE OBJETO CONTRATO (MANTIDO PARA GARANTIR QUE O EXEMPLO FUNCIONE SEM DB)
class MockContrato:
    def __init__(self, id):
        self.nome = "Empresa Exemplo S.A."
        self.cnpj = "12.345.678/0001-90"
        self.valor_contrato = "15000,00" # String que precisa de limpeza
        self.inicio_contrato = datetime.date(2025, 1, 1)
        self.termino_contrato = datetime.date(2026, 1, 1)
        self.abrangencia_contrato = "Serviços de Automação Predial"
        self.tipo_indice = "IPCA"
        self.estado = "SP"
        self.cep = "01310-100"
        self.endereco = "Avenida Paulista, 1200" # Apenas a rua/avenida + número
        self.cidade = "São Paulo" # Adicionando cidade, que o PDF Generator espera!
        self.telefone = "(11) 9999-8888"
        self.email = "contato@exemplo.com"
        self.clausuras_adicionais = "O escopo inclui suporte remoto 24/7."
        self.id = id


# --- Modelos de Banco de Dados ---

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False) 
    password_hash = db.Column(db.String(128))
    contratos = db.relationship('Contrato', backref='autor', lazy='dynamic')

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class Contrato(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    
    nome = db.Column(db.String(100), nullable=False)
    cnpj = db.Column(db.String(18), unique=True, nullable=False)
    
    # Novos campos do Contrato
    valor_contrato = db.Column(db.String(50), nullable=False) # Armazenamos como String (R$ 0.000,00)
    inicio_contrato = db.Column(db.Date, nullable=False)
    termino_contrato = db.Column(db.Date, nullable=False)
    abrangencia_contrato = db.Column(db.String(200), nullable=False)
    tipo_indice = db.Column(db.String(50), nullable=False) # Ex: IPCA, IGP-M, Fixo, etc.

    # Dados de Contato/Endereço
    estado = db.Column(db.String(2), nullable=False)
    cep = db.Column(db.String(9), nullable=False)
    endereco = db.Column(db.String(200), nullable=False)
    telefone = db.Column(db.String(15), nullable=False)
    email = db.Column(db.String(120), nullable=False)
    
    clausulas_adicionais = db.Column(db.Text, nullable=True)

    def __repr__(self):
        return f'<Contrato {self.nome} - {self.id}>'

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# --- FUNÇÕES DE AJUDA E FILTROS JINJA ---

def clean_currency_br(formatted_value):
    """
    Limpa a string formatada em moeda (R$ 1.234,56) para um objeto Decimal (1234.56),
    ideal para salvar no banco de dados.
    """
    if formatted_value is None or formatted_value == '':
        return decimal.Decimal('0.00')
    
    # Se já for Decimal, retorna
    if isinstance(formatted_value, decimal.Decimal):
        return formatted_value

    try:
        # 1. Remove R$ e espaços
        clean_value = str(formatted_value).replace('R$', '').strip()
        # 2. Remove o ponto de milhar
        clean_value = clean_value.replace('.', '')
        # 3. Substitui a vírgula decimal por ponto (padrão Python/Decimal)
        clean_value = clean_value.replace(',', '.')
        
        # 4. Converte para Decimal
        return decimal.Decimal(clean_value)
    except decimal.InvalidOperation:
        # Em caso de falha, retorna 0.00 ou levanta erro para o WTForms
        return decimal.Decimal('0.00')

# --- FUNÇÕES DE AJUDA E FILTROS JINJA ---

def clean_currency_br(formatted_value):
    """
    Limpa a string formatada em moeda (R$ 1.234,56) para um objeto Decimal (1234.56),
    ideal para salvar no banco de dados.
    """
    if formatted_value is None or formatted_value == '':
        return decimal.Decimal('0.00')
    
    # Se já for Decimal, retorna
    if isinstance(formatted_value, decimal.Decimal):
        return formatted_value

    try:
        # 1. Remove R$ e espaços
        clean_value = str(formatted_value).replace('R$', '').strip()
        # 2. Remove o ponto de milhar
        clean_value = clean_value.replace('.', '')
        # 3. Substitui a vírgula decimal por ponto (padrão Python/Decimal)
        clean_value = clean_value.replace(',', '.')
        
        # 4. Converte para Decimal
        return decimal.Decimal(clean_value)
    except decimal.InvalidOperation:
        # Em caso de falha, retorna 0.00 ou levanta erro para o WTForms
        return decimal.Decimal('0.00')

def format_currency_br(value):
    """
    Formata um valor float, decimal ou string (com R$, . e ,) 
    como moeda no padrão Brasileiro (R$ 1.000,00).

    CORREÇÃO CRÍTICA: Adiciona tratamento para 'value' ser uma string,
    que é o que causava o TypeError no 'abs()'.
    """
    
    # === CORREÇÃO CRÍTICA PARA ERRO 500 ===
    # Se o valor for uma string (input cru do formulário), limpa e converte.
    if isinstance(value, str):
        try:
            # Usa a sua função de limpeza para obter um objeto Decimal
            value = clean_currency_br(value) 
        except Exception:
            # Em caso de falha, usa 0.0 para evitar o crash no 'abs()' do locale.
            value = 0.0
    # === FIM DA CORREÇÃO ===

    try:
        # Tenta configurar o locale para pt_BR com codificação UTF-8
        locale.setlocale(locale.LC_ALL, 'pt_BR.UTF-8')
    except locale.Error:
        try:
            # Fallback para 'pt_BR'
            locale.setlocale(locale.LC_ALL, 'pt_BR')
        except locale.Error:
            # Fallback forçando a formatação manual (menos ideal)
            if value is None:
                return "R$ 0,00"
            # Certifique-se que o valor é float/decimal para formatar manualmente
            value_float = float(value) if value is not None else 0.0
            return f"R$ {value_float:,.2f}".replace('.', '#').replace(',', '.').replace('#', ',')

    if value is None:
        value = 0.0

    # Formata o valor como moeda. O locale configurado define o R$ e o separador.
    formatted_value = locale.currency(value, grouping=True, symbol=True)
    return formatted_value

def format_date_br(date_obj, include_day=True):
    """Formata objeto datetime.date para DD de MÊS de AAAA ou MÊS de AAAA."""
    
    nomes_meses = {
        1: 'janeiro', 2: 'fevereiro', 3: 'março', 4: 'abril', 5: 'maio', 6: 'junho',
        7: 'julho', 8: 'agosto', 9: 'setembro', 10: 'outubro', 11: 'novembro', 12: 'dezembro'
    }

    data_formatada = None
    
    # Lógica para converter data (se for string)
    if isinstance(date_obj, date):
        data_formatada = date_obj
    elif date_obj and isinstance(date_obj, str):
        try:
            data_formatada = date.fromisoformat(date_obj) 
        except ValueError:
            try:
                data_formatada = datetime.strptime(date_obj, '%d/%m/%Y').date()
            except ValueError:
                return date_obj

    if data_formatada:
        mes_extenso = nomes_meses.get(data_formatada.month, str(data_formatada.month))
        if include_day:
            return f"{data_formatada.day} de {mes_extenso} de {data_formatada.year}"
        else:
            return f"{mes_extenso} de {data_formatada.year}"
    
    return 'N/A'

def limpar_valor_moeda(valor_str):
    """Remove R$, pontos de milhar, substitui vírgula por ponto e converte para float."""
    if isinstance(valor_str, (float, int)):
        return valor_str
    
    if not isinstance(valor_str, str):
        return 0.0

    # Remove R$, símbolos de moeda, e pontos de milhar
    limpo = re.sub(r'[R$]', '', valor_str.strip())
    limpo = re.sub(r'\.', '', limpo)
    
    # Substitui a vírgula decimal por ponto decimal
    limpo = limpo.replace(',', '.')
    
    try:
        return float(limpo)
    except ValueError:
        print(f"Aviso: Não foi possível converter o valor '{valor_str}' para numérico.")
        return 0.0

# Mock da função de geração de PDF Reportlab. 
# Apenas retorna um buffer vazio para que a rota 'download_pdf' funcione sem erro.
def gerar_pdf_reportlab(data):
    """Mock da função real. Retorna um buffer de Bytes."""
    # A rota download_pdf espera que esta função retorne um objeto com o método .getvalue()
    pdf_buffer = io.BytesIO()
    # Adicione conteúdo dummy se necessário, mas para rodar o app, isso é suficiente
    pdf_buffer.write(b'%PDF-1.4\n1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n') 
    pdf_buffer.seek(0)
    return pdf_buffer

# Mock da função de geração de PDF (a outra versão)
def generate_contract_pdf(data):
    """Mock da função real para a rota /gerar_pdf."""
    pdf_buffer = io.BytesIO()
    pdf_buffer.write(b'%PDF-1.4\n1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n') 
    pdf_buffer.seek(0)
    return pdf_buffer

# --- REGISTRO DOS FILTROS JINJA ---
# Esta linha AGORA está correta, pois a função format_currency_br está definida acima.
app.jinja_env.filters['currency_br'] = format_currency_br
app.jinja_env.filters['date_br'] = format_date_br


# --- Formulários WTForms ---

class RegistrationForm(FlaskForm):
    username = StringField('Usuário', validators=[DataRequired(), Length(min=2, max=20)])
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Senha', validators=[DataRequired()])
    password2 = PasswordField('Repita a Senha', validators=[DataRequired(), EqualTo('password')])
    submit = SubmitField('Cadastrar')

    def validate_username(self, username):
        user = User.query.filter_by(username=username.data).first()
        if user:
            raise ValidationError('Este nome de usuário já está em uso.')

    def validate_email(self, email):
        user = User.query.filter_by(email=email.data).first()
        if user:
            raise ValidationError('Este email já está registrado.')

class LoginForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Email()]) 
    password = PasswordField('Senha', validators=[DataRequired()])
    submit = SubmitField('Entrar')

# A CLASSE ContratoForm (AGORA COM FILTRO DE LIMPEZA E INDENTAÇÃO CORRETA)
# A CLASSE ContratoForm (AGORA COM FILTRO DE LIMPEZA E INDENTAÇÃO CORRETA)
class ContratoForm(FlaskForm):
    # CORREÇÃO CRÍTICA: Adicionar __init__ para aceitar o ID do contrato
    def __init__(self, *args, contrato_id=None, **kwargs):
        super(ContratoForm, self).__init__(*args, **kwargs)
        self.contrato_id = contrato_id # Armazena o ID para uso na validação
    
    nome = StringField('Razão Social', validators=[DataRequired(), Length(max=100)])
    
    cnpj = StringField('CNPJ', validators=[
        DataRequired(),
        Length(min=18, max=18, message="CNPJ deve ter 14 dígitos e estar formatado (XX.XXX.XXX/XXXX-XX)."),
        Regexp(r'^\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2}$', message="Formato do CNPJ inválido.")
    ])
    
    # =====================================================================
    # CAMPO VALOR_CONTRATO - Regexp REMOVIDO!
    valor_contrato = StringField(
        'Valor do Contrato', 
        validators=[
            DataRequired(), 
            # Validador Regexp removido!
            # Sua função clean_currency_br já trata a limpeza/conversão.
        ],
        # FILTRO CRÍTICO QUE LIMPA E CONVERTE PARA DECIMAL
        filters=[clean_currency_br] 
    )
    # =====================================================================
    
    tipo_indice = SelectField('Índice de Reajuste', choices=[
        ('IPCA', 'IPCA (Índice Nacional de Preços ao Consumidor Amplo)'),
        ('IGP-M', 'IGP-M (Índice Geral de Preços - Mercado)'),
        ('INPC', 'INPC (Índice Nacional de Preços ao Consumidor)'),
        ('Outro', 'Outro / Fixo'),
    ], validators=[DataRequired()])
    inicio_contrato = DateField('Início do Contrato', format='%Y-%m-%d', validators=[DataRequired()])
    termino_contrato = DateField('Término do Contrato', format='%Y-%m-%d', validators=[DataRequired()])
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
    email = StringField('E-mail', validators=[DataRequired(), Email(), Length(max=120)])
    
    clausulas_adicionais = TextAreaField('Cláusulas Adicionais', validators=[Optional()])

    submit = SubmitField('Salvar Contrato')

    def validate_cnpj(self, cnpj):
        cleaned_cnpj = cnpj.data
        query = Contrato.query.filter_by(cnpj=cleaned_cnpj)
        
        # O __init__ agora garante que self.contrato_id esteja presente
        if self.contrato_id is not None:
            # Exclui o contrato atual da checagem para permitir a edição
            query = query.filter(Contrato.id != self.contrato_id)
        
        contrato = query.first()
        if contrato:
            raise ValidationError('Este CNPJ já está cadastrado.')

class SearchForm(FlaskForm):
    termo = StringField('Busca', validators=[Length(max=50)])
    submit = SubmitField('Buscar')


# --- Rotas de Autenticação ---

@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    form = RegistrationForm()
    if form.validate_on_submit():
        user = User(username=form.username.data, email=form.email.data)
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()
        flash('Sua conta foi criada com sucesso! Faça login.', 'success')
        return redirect(url_for('login'))
    return render_template('register.html', form=form)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user and user.check_password(form.password.data):
            login_user(user)
            next_page = request.args.get('next')
            flash(f'Login realizado com sucesso! Bem-vindo(a), {user.username}.', 'success')
            return redirect(next_page or url_for('index'))
        else:
            flash('Login sem sucesso. Verifique E-mail e senha.', 'error') 
    return render_template('login.html', form=form)

@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('index'))

# --- Rotas de Contratos ---

@app.route('/', methods=['GET', 'POST'])
@login_required
def index():
    form_cadastro = ContratoForm()
    
    # Dica: É mais seguro inicializar form_busca com request.form se o método for POST 
    # e com request.args se o método for GET. No contexto da sua lógica de busca GET,
    # SearchForm(request.args) está OK, mas SearchForm() é mais comum quando o formulário
    # não está sendo validado via POST. Vou manter o seu, mas é bom saber.
    form_busca = SearchForm(request.args) 
    
    if form_cadastro.validate_on_submit():
        try:
            # Converte o objeto Decimal (que veio do form.data) para string
            # antes de salvar no banco de dados SQLite.
            valor_para_salvar = str(form_cadastro.valor_contrato.data) 
            
            novo_contrato = Contrato(
                user_id=current_user.id,
                nome=form_cadastro.nome.data,
                cnpj=form_cadastro.cnpj.data,
                
                # MUDANÇA CRÍTICA: Salva a string formatada
                valor_contrato=valor_para_salvar, 
                
                inicio_contrato=form_cadastro.inicio_contrato.data,
                termino_contrato=form_cadastro.termino_contrato.data,
                abrangencia_contrato=form_cadastro.abrangencia_contrato.data,
                tipo_indice=form_cadastro.tipo_indice.data,
                estado=form_cadastro.estado.data,
                cep=form_cadastro.cep.data,
                endereco=form_cadastro.endereco.data,
                telefone=form_cadastro.telefone.data,
                email=form_cadastro.email.data,
                clausulas_adicionais=form_cadastro.clausulas_adicionais.data
            )
            
            db.session.add(novo_contrato)
            db.session.commit()
            flash('Contrato cadastrado com sucesso!', 'success')
            return redirect(url_for('index'))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Erro ao cadastrar o contrato: {e}', 'danger') 
            print(f"Erro no cadastro: {e}") 
            
    elif request.method == 'POST':
        print("\n--- ERROS DE VALIDAÇÃO DO FORMULÁRIO DE CADASTRO ---")
        for field, errors in form_cadastro.errors.items():
            print(f"Campo '{field}': {errors}")
        print("--------------------------------------------------\n")
        flash('Falha no cadastro. Verifique os campos com erro abaixo.', 'error')

    # Lógica de Busca (GET)
    contratos_query = Contrato.query.filter_by(user_id=current_user.id)
    
    if form_busca.termo.data:
        termo = f"%{form_busca.termo.data}%"
        contratos_query = contratos_query.filter(
            (Contrato.nome.ilike(termo)) |
            (Contrato.cnpj.ilike(termo)) |
            (Contrato.cep.ilike(termo))
        )
    
    contratos = contratos_query.order_by(Contrato.id.desc()).all()
    # Criação do formulário de exclusão
    form_exclusao = ExclusaoContratoForm()

    # CORREÇÃO: form_exclusao AGORA É PASSADO PARA O TEMPLATE
    return render_template('index.html', 
                           form_cadastro=form_cadastro, 
                           form_busca=form_busca, 
                           contratos=contratos,
                           form_exclusao=form_exclusao)
    

# --- Rota de Edição de Contrato (Correta) ---
@app.route('/contrato/editar/<int:id>', methods=['GET', 'POST'])
@login_required
def editar_contrato(id):
    contrato = Contrato.query.get_or_404(id)

    # Verificação de segurança (IDOR)
    if contrato.user_id != current_user.id:
        flash('Você não tem permissão para editar este contrato.', 'error')
        return redirect(url_for('index'))
    
    # CRÍTICO: Passa o contrato (obj) e o ID (contrato_id) para a validação
    form = ContratoForm(obj=contrato, contrato_id=contrato.id) 

    if form.validate_on_submit():
        form.populate_obj(contrato)
        try:
            db.session.commit()
            flash('Contrato atualizado com sucesso!', 'success')
            return redirect(url_for('index'))
        except Exception as e:
            db.session.rollback()
            flash(f'Erro ao salvar alterações: {e}', 'error')
            
    # GET request: Renderiza o formulário pré-preenchido
    return render_template('editar_contrato.html', form=form, contrato=contrato)


# --- Rota de Exclusão de Contrato (Corrigida) ---
@app.route("/contrato/excluir/<int:contrato_id>", methods=["POST"])
@login_required # Garante que só usuários logados podem excluir
def excluir_contrato(contrato_id):
    try:
        # CORREÇÃO 1: Usa o parâmetro correto 'contrato_id' na busca e garante o 404
        contrato = Contrato.query.get_or_404(contrato_id)

        # Verificação de segurança (IDOR)
        if contrato.user_id != current_user.id:
            flash('Você não tem permissão para excluir este contrato.', 'error')
            return redirect(url_for('index'))
            
        # CORREÇÃO 2: Usa o método nativo do SQLAlchemy para exclusão (db.session.delete)
        db.session.delete(contrato)
        db.session.commit()
        flash(f"Contrato {contrato_id} excluído com sucesso!", 'success')
        
    except Exception as e:
        db.session.rollback() # Garante que se houver erro, a transação é desfeita
        print(f"Erro ao tentar excluir contrato {contrato_id}: {e}")
        flash(f"Ocorreu um erro ao tentar excluir o contrato: {e}", 'danger')
        
    return redirect(url_for('index'))

# --- Rota de Geração de PDF (Corrigida) ---
@app.route('/gerar_pdf/<int:id>', methods=['GET'])
@login_required
def gerar_pdf(id):
    # Apenas uma chamada para obter o contrato, removendo a duplicidade anterior
    contrato = Contrato.query.get_or_404(id) 

    # Verificação de segurança (IDOR)
    if contrato.user_id != current_user.id:
        flash('Você não tem permissão para gerar o PDF deste contrato.', 'error')
        return redirect(url_for('index'))
    
    # Prepara os dados do objeto SQLAlchemy para o gerador de PDF
    contrato_data = {
        'nome': contrato.nome,
        'cnpj': contrato.cnpj,
        'telefone': contrato.telefone,
        'email': contrato.email,
        # CORREÇÃO PRINCIPAL: Adicionando a chave ausente que o gerador de PDF espera
        'contratante_completo': (
            f"{contrato.nome}, inscrito sob o CNPJ {contrato.cnpj}, com sede em "
            f"{contrato.endereco}, CEP {contrato.cep}, {contrato.estado}. "
            f"Contato principal: Tel. {contrato.telefone}, E-mail: {contrato.email}."
        ),
        'valor_contrato': contrato.valor_contrato, 
        'inicio_contrato': contrato.inicio_contrato.strftime('%Y-%m-%d'),
        'termino_contrato': contrato.termino_contrato.strftime('%Y-%m-%d'),
        'abrangencia_contrato': contrato.abrangencia_contrato,
        'tipo_indice': contrato.tipo_indice,
        'endereco': contrato.endereco,
        'cidade': 'N/A', # Mantido 'N/A' pois não existe no modelo
        'estado': contrato.estado,
        'cep': contrato.cep,
        'clausulas_adicionais': contrato.clausulas_adicionais
    }
    
    try:
        # 2. Chama a função do arquivo separado para gerar o PDF
        pdf_buffer = generate_contract_pdf(contrato_data)
        
        # 3. Cria a resposta HTTP
        response = make_response(pdf_buffer.getvalue())
        response.headers['Content-Type'] = 'application/pdf'
        
        filename_name = contrato.nome.replace(' ', '_').replace('/', '').replace('.', '')
        response.headers['Content-Disposition'] = f'attachment; filename=Contrato_{filename_name}.pdf'
        
        return response
    except Exception as e:
        flash(f"Erro ao gerar o PDF: {e}", 'error')
        print(f"Erro ao gerar o PDF: {e}")
        return redirect(url_for('index'))
    
    # --- NOVA ROTA: Visualizar Cláusulas ---
@app.route('/clausulas/<int:id>', methods=['GET'])
@login_required
def ver_clausulas(id):
    """
    Exibe os detalhes completos, incluindo cláusulas adicionais, de um contrato específico.
    """
    try:
        contrato = Contrato.query.get_or_404(id)
        # Se for necessário carregar um formulário para edição das cláusulas, você pode passá-lo aqui.
        # Por enquanto, apenas renderizamos o contrato.
        return render_template('clausulas_adicionais.html', contrato=contrato)
    except Exception as e:
        flash(f'Erro ao carregar o contrato: {e}', 'danger')
        return redirect(url_for('index'))

@app.route('/download_pdf/<int:id>', methods=['GET'])
# Se você usa Flask-Login:
@login_required 
def download_pdf(id):
    # Supondo que você tem a classe Contrato e a variável db
    # contrato = Contrato.query.get_or_404(id) 
    
    # --- MOCK DE OBJETO CONTRATO (REMOVER EM PRODUÇÃO) ---
    # Coloquei o mock aqui para garantir que o código funcione ao ser executado em ambientes de teste.
    class MockContrato:
        def __init__(self, id=None):
            self.nome = "Empresa Exemplo S.A."
            self.cnpj = "12.345.678/0001-90"
            self.valor_contrato = "15000,00" # String que precisa de limpeza
            self.inicio_contrato = datetime.date(2025, 1, 1)
            self.termino_contrato = datetime.date(2026, 1, 1)
            self.abrangencia_contrato = "Serviços de Automação Predial"
            self.tipo_indice = "IPCA"
            self.estado = "SP"
            self.cep = "01310-100"
            self.endereco = "Avenida Paulista, 1200" # Apenas a rua/avenida + número
            self.cidade = "São Paulo" # Adicionando cidade, que o PDF Generator espera!
            self.telefone = "(11) 9999-8888"
            self.email = "contato@exemplo.com"
            self.clausulas_adicionais = "O escopo inclui suporte remoto 24/7." # CORRETO NO MOCK
            self.id = id
    
    try:
        # Tenta buscar o contrato real (descomente e ajuste no seu app)
        # contrato = Contrato.query.get_or_404(id) 
        contrato = MockContrato() # Deixe o mock ativo para teste
    except NameError:
        # Caso Contrato não esteja definido (somente para testes)
        contrato = MockContrato() 
    # --- FIM DO MOCK ---
    
    try:
        # 1. LIMPAR E FORMATAR VALOR (usando a função de ajuda)
        valor_numerico = limpar_valor_moeda(contrato.valor_contrato)
        # format_currency_br está agora no pdf_generator.py, vamos usá-lo ou a versão do locale
        
        # O SEU pdf_generator.py usa a chave 'valor_contrato' no dicionário 'data',
        # mas formata internamente com format_currency_br(data.get('valor_contrato', 0)).
        # Portanto, vamos garantir que o valor seja passado em um formato que ele consiga ler.
        
        # Preparando o dicionário de dados que será passado para gerar_pdf_reportlab
        contrato_data = {
            # DADOS PRINCIPAIS (O SEU PDF espera o valor bruto ou limpo, não a string formatada)
            'nome': contrato.nome,
            'cnpj': contrato.cnpj,
            # Passando o valor numericamente limpo para que o format_currency_br dentro do PDF funcione
            'valor_contrato': valor_numerico, 
            'inicio_contrato': contrato.inicio_contrato, # Passa o objeto date, pois format_date_br aceita
            'termino_contrato': contrato.termino_contrato, # Passa o objeto date
            'abrangencia_contrato': contrato.abrangencia_contrato, 
            'tipo_indice': contrato.tipo_indice, 
            
            # DADOS DE ENDEREÇO E CONTATO (CHAVES ESSENCIAIS PARA O SEU MODELO)
            # O SEU PDF Generator usa explicitamente estas 5 chaves:
            'endereco': contrato.endereco, 
            'cidade': getattr(contrato, 'cidade', 'São Paulo'), # Usa o campo cidade, ou um valor padrão se não existir no modelo
            'estado': contrato.estado,
            'cep': contrato.cep,
            'telefone': contrato.telefone,
            
            # OUTROS DADOS
            'email': contrato.email,
            # CORREÇÃO AQUI: Troquei 'clausuras_adicionais' por 'clausulas_adicionais'
            'clausulas_adicionais': contrato.clausulas_adicionais if hasattr(contrato, 'clausulas_adicionais') else 'Nenhuma cláusula adicional.',
        }
        
        # 2. Chama a função de geração de PDF (agora usando o nome correto)
        # OBS: Assumindo que 'gerar_pdf_reportlab' está importado ou definido no escopo
        pdf_buffer = gerar_pdf_reportlab(contrato_data)
        
        # 3. Retorna o PDF como um anexo para download
        filename = f"Contrato_{contrato.nome.replace(' ', '_')}_{contrato.cnpj.replace('/', '-')}.pdf"
        
        return send_file(
            pdf_buffer, 
            mimetype='application/pdf', 
            as_attachment=True, 
            download_name=filename
        )

    except Exception as e:
        # app.logger.error deve estar importado do Flask
        # app.logger.error(f"Erro na geração de PDF para o contrato ID {id}: {e}", exc_info=True)
        # flash e redirect devem estar importados do Flask
        # flash(f'Erro interno ao gerar o PDF. Detalhes: {e}', 'danger')
        return redirect(url_for('index'))




# ... (O restante do seu código, como a rota de login, etc.)


# --- Inicialização ---

if __name__ == '__main__':
    with app.app_context():
        if User.query.filter_by(username='teste').first() is None:
            user = User(username='teste', email='teste@teste.com')
            user.set_password('senha123')
            db.session.add(user)
            db.session.commit()
            print("Usuário 'teste' (email: teste@teste.com, senha: senha123) criado com sucesso.")

    app.run(debug=False)