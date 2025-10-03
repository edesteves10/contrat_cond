import os
from datetime import datetime
import sqlite3
from flask import Flask, render_template, request, redirect, url_for, send_file, flash, session
from flask_sqlalchemy import SQLAlchemy
from flask import send_file
from reportlab.pdfgen import canvas
from io import BytesIO
import re 
from decimal import Decimal
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch, cm
from PIL import Image as PIL_Image
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT # TA_LEFT já está aqui, vamos usar
from reportlab.lib.fonts import addMapping
from reportlab.platypus import Paragraph, Spacer, Image
from reportlab.pdfbase import pdfmetrics as pdfmetrics_base
from reportlab.pdfbase.ttfonts import TTFont
from flask import jsonify
from flask_wtf import FlaskForm
from wtforms import StringField, DateField, DecimalField, SelectField, SubmitField, EmailField
from wtforms.validators import DataRequired, Length, Regexp, Optional, NumberRange # <-- Adicione NumberRange aqui!
from wtforms.widgets import TextInput # Importar TextInput para forçar o tipo text

# Se você já tem a classe ContratoForm, altere apenas o valor_contrato
class ContratoForm(FlaskForm):
    nome = StringField('Nome', validators=[DataRequired(), Length(max=100)])
    cnpj = StringField('CNPJ', validators=[DataRequired(), Length(min=14, max=18)])
    endereco = StringField('Endereço', validators=[DataRequired(), Length(max=200)])
    cep = StringField('CEP', validators=[DataRequired(), Length(min=8, max=9)])
    estado = StringField('Estado', validators=[DataRequired(), Length(max=50)])
    telefone = StringField('Telefone', validators=[DataRequired(), Length(max=20)])
    email = EmailField('Email', validators=[DataRequired(), Length(max=100)])
    indice_reajuste = SelectField('Índice de Reajuste', choices=[('IPCA', 'IPCA'), ('IGPM', 'IGPM'), ('Nenhum', 'Nenhum')], default='IPCA')

    valor_contrato = DecimalField(
        'Valor do Contrato (R$)',
        validators=[Optional(), NumberRange(min=0)],
        render_kw={"placeholder": "Ex: 1.234,56", "type": "text"} # Adicione "type": "text"
    )
        
    
    inicio_contrato = DateField('Início do Contrato', format='%Y-%m-%d', validators=[DataRequired()])
    termino_contrato = DateField('Término do Contrato', format='%Y-%m-%d', validators=[Optional()])
    abrangencia_contrato = StringField('Abrangência do Contrato', validators=[DataRequired(), Length(max=100)])
    tipo_indice = StringField('Tipo de Índice de Reajuste', validators=[Optional(), Length(max=10)])
    submit = SubmitField('Salvar')

# Registrar a fonte Arial (se não estiver padrão no reportlab)
try:
    pdfmetrics_base.registerFont(TTFont('Arial', 'arial.ttf'))
    pdfmetrics_base.registerFont(TTFont('Arial-Bold', 'arialbd.ttf'))
except Exception as e:
    print(f"Erro ao registrar fontes Arial: {e}")

project_dir = os.path.dirname(os.path.abspath(__file__))
database_file = "sqlite:///{}".format(os.path.join(project_dir, "database.db"))

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your secret key'
app.config['SQLALCHEMY_DATABASE_URI'] = database_file
db = SQLAlchemy(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

with app.app_context():
    try:
        db.create_all()
        print("Tabelas criadas com sucesso (se não existirem).")
    except Exception as e:
        print(f"Erro ao criar tabelas: {e}")

@login_manager.user_loader
def load_user(user_id):
    try:
        return User.query.get(int(user_id))
    except ValueError:
        return None

class ContratCond(db.Model):
    id = db.Column(db.Integer, primary_key=True) # <--- CHAVE PRIMÁRIA CORRETA

    nome = db.Column(db.String(100), nullable=False)
    cnpj = db.Column(db.String(20), unique=True, nullable=False)
    endereco = db.Column(db.String(200), nullable=False)
    cep = db.Column(db.String(10), nullable=False)
    estado = db.Column(db.String(50), nullable=False)
    telefone = db.Column(db.String(20), nullable=False)
    email = db.Column(db.String(120), nullable=False)
    valor_contrato = db.Column(db.Numeric(10, 2), nullable=False)
    inicio_contrato = db.Column(db.Date, nullable=False)
    termino_contrato = db.Column(db.Date, nullable=True)
    abrangencia_contrato = db.Column(db.String(100), nullable=False)
    tipo_indice = db.Column(db.String(50), nullable=True)
    data_criacao = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    
    # Exemplo de coluna de data de criação (opcional, mas boa prática)
    data_criacao = db.Column(db.DateTime, default=datetime.utcnow) 

    def __repr__(self):
        return f'<ContratCond {self.nome}>'

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        if username and password:
            try:
                user = User.query.filter_by(username=username).first()
                print(f"Nome de usuário digitado: {username}")
                print(f"Senha digitada: {password}")
                if user:
                    print(f"Usuário encontrado no banco de dados: {user.username}")
                    if user.check_password(password):
                        print("Senha verificada com sucesso.")
                        login_user(user)
                        return redirect(request.args.get('next') or url_for('index'))
                    else:
                        print("Senha incorreta.")
                        flash('Usuário ou senha incorretos.', 'error')
                else:
                    print("Usuário não encontrado.")
                    flash('Usuário ou senha incorretos.', 'error')
            except Exception as e:
                print(f"Erro durante o login: {e}")
                flash('Ocorreu um erro ao tentar fazer login.', 'error')
        else:
            flash('Por favor, preencha todos os campos.', 'warning')
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

@app.route('/', methods=['GET', 'POST'])
@login_required
def index():
    form = ContratoForm() # <--- INSTANCIE O FORMULÁRIO AQUI

    # ==========================================================
    # LÓGICA DE PROCESSAMENTO DO FORMULÁRIO (POST)
    # Esta parte permanece para adicionar novos contratos
    # ==========================================================
    if form.validate_on_submit():
        # ... (Sua lógica de extração de dados do formulário) ...
        nome = form.nome.data
        cnpj = form.cnpj.data
        endereco = form.endereco.data
        cep = form.cep.data
        estado = form.estado.data
        telefone = form.telefone.data
        email = form.email.data
        tipo_indice = form.tipo_indice.data # Novo campo
        valor_contrato = form.valor_contrato.data
        inicio_contrato = form.inicio_contrato.data
        termino_contrato = form.termino_contrato.data
        abrangencia_contrato = form.abrangencia_contrato.data

        novo_contrato = ContratCond(
            nome=nome, cnpj=cnpj, endereco=endereco, cep=cep, estado=estado,
            telefone=telefone, email=email, tipo_indice=tipo_indice, # Adicione o novo campo
            valor_contrato=valor_contrato, inicio_contrato=inicio_contrato,
            termino_contrato=termino_contrato, abrangencia_contrato=abrangencia_contrato
        )
        db.session.add(novo_contrato)
        db.session.commit()
        flash('Contrato adicionado com sucesso!', 'success')
        
        # Redireciona para a página principal (agora sem lista de contratos)
        return redirect(url_for('index'))
    else:
        # Se o formulário não validar no POST ou for um GET request
        for field, errors in form.errors.items():
            for error in errors:
                flash(f"Erro no campo '{getattr(form, field).label.text}': {error}", 'danger')

    # ==========================================================
    # LÓGICA DE VISUALIZAÇÃO E PESQUISA (GET)
    # ==========================================================
    
    # Obtém os parâmetros da URL
    page = request.args.get('page', 1, type=int)
    search_query = request.args.get('query', type=str)
    per_page = 5
    
    # Inicializa 'contratos' como None para que a tabela não seja exibida por padrão
    contratos = None
    
    # A lista de contratos SÓ SERÁ CARREGADA se houver um termo de pesquisa (search_query)
    if search_query:
        # Se o termo de pesquisa existir, filtramos o banco de dados
        # O .ilike() permite pesquisar de forma case-insensitive
        
        # ATENÇÃO: SUBSTITUA ESTA LÓGICA PELO SEU CÓDIGO REAL DE PESQUISA.
        # Estamos pesquisando pelo Nome OU pelo CNPJ.
        search_pattern = f"%{search_query}%"
        
        query = ContratCond.query.filter(
            (ContratCond.nome.ilike(search_pattern)) | 
            (ContratCond.cnpj.ilike(search_pattern))
        ).order_by(ContratCond.data_criacao.desc())
        
        # Paginação dos resultados da pesquisa
        contratos = query.paginate(page=page, per_page=per_page)
    
    
    # Passamos contratos e o termo de pesquisa para o template
    # Se 'search_query' for None, 'contratos' também será None, e o HTML esconderá a tabela.
    return render_template('index.html', 
                           form=form, 
                           contratos=contratos, 
                           search_query=search_query)

# Note: 'mostrar_apenas_ultimos = True' e 'search_query=None' não são mais necessários
# no contexto, pois são definidos ou calculados logo acima.
    
@app.route('/add_contrato', methods=['GET', 'POST'])
@login_required
def add_contrato():
    form = ContratoForm()
    if form.validate_on_submit():
        novo_cnpj = form.cnpj.data
        valor_contrato_str = form.valor_contrato.data
        try:
            novo_valor = float(valor_contrato_str.replace('.', '').replace(',', '.'))
        except ValueError:
            flash('Formato de valor do contrato inválido. Use o formato 1.234,56', 'danger')
            return render_template('add_contrato.html', form=form)

        novo_inicio = form.inicio_contrato.data
        novo_termino = form.termino_contrato.data

        contrato_existente = ContratCond.query.filter_by(
            cnpj=novo_cnpj,
            valor_contrato=novo_valor,
            inicio_contrato=novo_inicio,
            termino_contrato=novo_termino
        ).first()

        if contrato_existente:
            flash('Já existe um contrato com o mesmo CNPJ, valor de contrato, data de início e data de término.', 'danger')
            return render_template('add_contrato.html', form=form)
        else:
            try:
                contrato = ContratCond(
                    nome=form.nome.data,
                    cnpj=novo_cnpj,
                    endereco=form.endereco.data,
                    cep=form.cep.data,
                    estado=form.estado.data,
                    telefone=form.telefone.data,
                    email=form.email.data,
                    valor_contrato=novo_valor,
                    inicio_contrato=novo_inicio,
                    termino_contrato=novo_termino,
                    abrangencia_contrato=form.abrangencia_contrato.data,
                    tipo_indice=form.tipo_indice.data,
                    created=datetime.utcnow()
                )
                db.session.add(contrato)
                db.session.commit()
                flash('Contrato adicionado com sucesso!', 'success')
                return redirect(url_for('index'))
            except Exception as e:
                db.session.rollback()
                flash(f'Erro ao adicionar contrato: {e}', 'danger')
                return render_template('add_contrato.html', form=form)

    return render_template('add_contrato.html', form=form)

   
@app.route('/edit/<int:id>', methods=['GET', 'POST'])
@login_required
def edit(id):
    contrato = ContratCond.query.get_or_404(id)
    # Popula o formulário com os dados existentes do contrato para o GET request
    # ou para re-exibir o formulário com erros de validação
    form = ContratoForm(obj=contrato) 

    # Este bloco só é executado se o formulário for submetido (POST) 
    # E os validadores Flask-WTF forem passados (validate_on_submit())
    if form.validate_on_submit():
        try:
            # Lógica específica para o valor_contrato (conversão de string para float)
            valor_contrato_str = form.valor_contrato.data
            if valor_contrato_str: # Apenas tente converter se houver valor
                try:
                    # Remover pontos de milhar e substituir vírgula por ponto decimal
                    contrato.valor_contrato = float(valor_contrato_str.replace('.', '').replace(',', '.'))
                except ValueError:
                    flash('Formato de valor do contrato inválido. Use o formato 1.234,56', 'danger')
                    # Se a conversão do valor falhar, retorna para a página de edição com o formulário
                    return render_template('editar.html', form=form, contrato=contrato)
            else:
                contrato.valor_contrato = 0.0 # Define um valor padrão se estiver vazio


            # --- ATUALIZAÇÃO DE TODOS OS OUTROS CAMPOS DO CONTRATO ---
            # O form.populate_obj(contrato) faria isso automaticamente para todos os campos mapeados,
            # mas se você está fazendo manualmente, precisa incluir todos:
            contrato.nome = form.nome.data
            contrato.cnpj = form.cnpj.data
            contrato.endereco = form.endereco.data
            contrato.cep = form.cep.data
            contrato.estado = form.estado.data
            contrato.telefone = form.telefone.data
            contrato.email = form.email.data
            # As datas já devem vir como objetos date/datetime se o DateField estiver correto no formulário
            contrato.inicio_contrato = form.inicio_contrato.data 
            contrato.termino_contrato = form.termino_contrato.data
            contrato.abrangencia_contrato = form.abrangencia_contrato.data
            contrato.tipo_indice = form.tipo_indice.data # <<< ESTA LINHA É CRÍTICA PARA SALVAR O TIPO DE ÍNDICE
            
            # --- UM ÚNICO BLOCO TRY/EXCEPT PARA O COMMIT NO BANCO DE DADOS ---
            db.session.commit() # Tenta salvar as alterações no banco de dados
            flash('Contrato atualizado com sucesso!', 'success')
            return redirect(url_for('index')) # Redireciona para a página principal após o sucesso

        except Exception as e:
            db.session.rollback() # Desfaz a transação em caso de erro no banco
            flash(f'Erro ao salvar as alterações no banco de dados: {e}', 'danger')
            # Retorna para o formulário com o erro (mantém os dados preenchidos)
            return render_template('editar.html', form=form, contrato=contrato)
    
            # Atualiza os outros campos (use form.FIELD.data)
    contrato.nome = form.nome.data
    contrato.cnpj = form.cnpj.data
    contrato.endereco = form.endereco.data
    contrato.cep = form.cep.data
    contrato.estado = form.estado.data
    contrato.telefone = form.telefone.data
    contrato.email = form.email.data
        # As datas já devem vir como objetos date/datetime se o formato do DateField estiver correto e o banco não as converter para string
    contrato.inicio_contrato = form.inicio_contrato.data 
    contrato.termino_contrato = form.termino_contrato.data
    contrato.abrangencia_contrato = form.abrangencia_contrato.data
    contrato.tipo_indice = form.tipo_indice.data
        
    try:
            db.session.commit()
            flash('Contrato atualizado com sucesso!', 'success')
            return redirect(url_for('index'))
    except Exception as e:
            db.session.rollback() # Em caso de erro ao commitar no DB, desfaz a transação
            flash(f'Erro ao salvar as alterações no banco de dados: {e}', 'danger')
            # Retorna para o formulário com o erro
            return render_template('editar.html', form=form, contrato=contrato)
    
    # Este bloco é executado quando a requisição é GET (carregando a página de edição pela primeira vez)
    # ou se form.validate_on_submit() retornar False por algum motivo (ex: campos DataRequired vazios)
    return render_template('editar.html', form=form, contrato=contrato)


@app.route('/search', methods=['POST'])
@login_required
def search():
    form = ContratoForm() # <--- INSTANCIE O FORMULÁRIO AQUI TAMBÉM
    query = request.form.get('query')
    page = request.args.get('page', 1, type=int)
    per_page = 5

    search_results = ContratCond.query.filter(
        (ContratCond.nome.ilike(f'%{query}%')) | 
        (ContratCond.cnpj.ilike(f'%{query}%'))
    ).order_by(ContratCond.created.desc()).paginate(page=page, per_page=per_page)
    
    # Passe a query de busca de volta para o template para manter o valor no campo de busca
    return render_template('index.html', contratos=search_results, search_query=query, mostrar_apenas_ultimos=False, form=form) # <--- PASSE O FORMULÁRIO AQUI

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        if username and password:
            try:
                existing_user = User.query.filter_by(username=username).first()
                if existing_user:
                    flash('Este nome de usuário já está em uso. Por favor, escolha outro.', 'warning')
                    return render_template('registro.html')
                else:
                    hashed_password = generate_password_hash(password)
                    new_user = User(username=username, password_hash=hashed_password)
                    db.session.add(new_user)
                    db.session.commit()
                    flash('Usuário registrado com sucesso!', 'success')
                    return redirect(url_for('login'))
            except Exception as e:
                db.session.rollback()
                flash(f'Erro ao registrar usuário: {e}', 'error')
        else:
            flash('Por favor, preencha todos os campos.', 'warning')
    return render_template('registro.html')

with app.app_context():
    try:
        db.create_all()
        print("Tabelas criadas com sucesso (na inicialização).")
    except Exception as e:
        print(f"Erro ao criar tabelas na inicialização: {e}")

# Certifique-se de que as importações listadas no Passo 1 estão no topo do arquivo.

@app.route('/pdf/<int:id>')
@login_required
def generate_pdf(id):
    contrato = ContratCond.query.get_or_404(id)

    try:
        output = BytesIO()
        
        # Definir margens e tamanho da página
        margem_superior = 2 * cm
        margem_inferior = 2 * cm
        margem_esquerda = 2 * cm
        margem_direita = 2 * cm
        page_width, page_height = letter # Letter: 8.5 x 11 polegadas

        # Cria o objeto Canvas
        p = canvas.Canvas(output, pagesize=letter)
        
        # --- Configuração dos Estilos de Parágrafo ---
        # As fontes 'Helvetica' e 'Helvetica-Bold' são padrão no ReportLab e funcionam no Heroku.
        styles = getSampleStyleSheet()
        
        # Estilo Base
        base_style = ParagraphStyle(
            name='Base',
            fontName='Helvetica', # Alterado de 'Arial' para 'Helvetica'
            fontSize=12,
            leading=14, # Espaçamento entre linhas
            alignment=TA_LEFT,
        )

        # Estilos específicos
        normal_style = base_style
        
        bold_style = ParagraphStyle(
            name='BoldStyle',
            parent=normal_style,
            fontName='Helvetica-Bold' # Alterado de 'Arial-Bold' para 'Helvetica-Bold'
        )
        
        centered_style = ParagraphStyle(
            name='Centered',
            parent=normal_style,
            alignment=TA_CENTER,
            fontName='Helvetica' # Alterado de 'Arial' para 'Helvetica'
        )
        
        centered_bold_style = ParagraphStyle(
            name='CenteredBold',
            parent=centered_style,
            fontName='Helvetica-Bold', # Alterado de 'Arial-Bold' para 'Helvetica-Bold'
            fontSize=15,
            spaceAfter=0.05 * cm # Espaço após o título da empresa
        )
        
        cnpj_style = ParagraphStyle(
            name='CNPJStyle',
            parent=centered_style,
            fontSize=10,
            spaceAfter=0.4 * cm # Espaço após o CNPJ
        )
        
        footer_style = ParagraphStyle(
            name='Footer',
            parent=normal_style, # Usar normal_style como pai para herdar fontName
            fontName='Helvetica', # Alterado de 'Arial' para 'Helvetica'
            fontSize=8, # Reduzido para caber bem no rodapé
            alignment=TA_CENTER
        )
        
        section_title_style = ParagraphStyle(
            name='SectionTitle',
            parent=centered_style,
            fontName='Helvetica-Bold', # Alterado de 'Arial-Bold' para 'Helvetica-Bold'
            fontSize=14,
            spaceAfter=0.5 * cm
        )
        
        right_aligned_style = ParagraphStyle(
            name='RightAligned',
            parent=normal_style,
            alignment=TA_RIGHT,
            fontName='Helvetica', # Alterado de 'Arial' para 'Helvetica'
            spaceAfter=0.5 * cm # Espaço após o bloco de local/data
        )

        # --- Variáveis de Posicionamento ---
        # Posição Y inicial para desenhar conteúdo, considerando a margem superior
        current_y = page_height - margem_superior

        # Largura da área de conteúdo (excluindo margens laterais)
        content_width = page_width - margem_esquerda - margem_direita

        # --- Cabeçalho da Página (Logo e Informações da Empresa) ---
        logo_path = os.path.join(app.root_path, 'static', 'logo.png') # Caminho do logo
        logo_width = 3.5 * cm # Largura desejada para o logo
        logo_height = 0 # Inicializado, será calculado pela proporção

        # Tenta carregar e posicionar o logo
        try:
            img = PIL_Image.open(logo_path)
            img_width_orig, img_height_orig = img.size
            aspect_ratio = img_height_orig / img_width_orig
            logo_height = logo_width * aspect_ratio

            logo_x = margem_esquerda # Posição X do logo
            logo_y = current_y - logo_height # Posição Y do canto inferior esquerdo do logo

            logo_obj = Image(logo_path, width=logo_width, height=logo_height)
            logo_obj.drawOn(p, logo_x, logo_y)
            
            # Atualiza a posição Y atual para abaixo do logo (ou do topo da margem se não tiver logo)
            current_y = min(current_y, logo_y) # Pega a menor Y ocupada pelo logo
        except FileNotFoundError:
            print(f"Erro: Logo não encontrado em {logo_path}")
            logo_height = 0 # Se o logo não existe, sua altura é 0 para o layout
        
        # Informações da Empresa (centralizadas verticalmente com o logo ou no topo se sem logo)
        empresa_nome_para = Paragraph("M.A. Automatização", centered_bold_style)
        cnpj_para = Paragraph("CNPJ: 27.857.310/0001-83", centered_style)

        # Calcula a altura total do bloco de texto da empresa
        _, empresa_nome_h = empresa_nome_para.wrapOn(p, content_width, page_height)
        _, cnpj_h = cnpj_para.wrapOn(p, content_width, page_height)
        total_text_h = empresa_nome_h + cnpj_h + 0.2 * cm # Espaço entre nome e CNPJ

        # Se houver logo, centraliza o texto da empresa com a altura do logo
        if logo_height > 0:
            text_block_start_y = (current_y + logo_height / 2) + total_text_h / 2
        else:
            text_block_start_y = page_height - margem_superior # Sem logo, começa do topo

        empresa_name_y = text_block_start_y - empresa_nome_h
        cnpj_y = empresa_name_y - cnpj_h - 0.2 * cm # Espaço entre

        # Desenha o texto da empresa, centralizado horizontalmente na área de conteúdo
        empresa_nome_width, _ = empresa_nome_para.wrapOn(p, content_width, page_height)
        cnpj_width, _ = cnpj_para.wrapOn(p, content_width, page_height)

        empresa_nome_para.drawOn(p, margem_esquerda + (content_width - empresa_nome_width) / 2, empresa_name_y)
        cnpj_para.drawOn(p, margem_esquerda + (content_width - cnpj_width) / 2, cnpj_y)

        # Atualiza o current_y para o ponto mais baixo do cabeçalho
        current_y = min(current_y, cnpj_y) 
        
        # Linha divisória do cabeçalho
        line_y = current_y - 0.5 * cm # 0.5 cm abaixo do elemento mais baixo do cabeçalho
        p.line(margem_esquerda, line_y, page_width - margem_direita, line_y)
        current_y = line_y - 0.5 * cm # Posição Y para o próximo conteúdo

        # --- Corpo do Contrato ---
        # Título "Informações do Contrato"
        section_title_para = Paragraph("Informações do Contrato", section_title_style)
        section_title_width, section_title_h = section_title_para.wrapOn(p, content_width, page_height)
        section_title_para.drawOn(p, margem_esquerda + (content_width - section_title_width) / 2, current_y - section_title_h)
        current_y -= section_title_h + 1 * cm # 1 cm de espaço após o título da seção

        # Local e Data Alinhados à Direita
        data_atual = datetime.now()
        meses = {
            1: 'janeiro', 2: 'fevereiro', 3: 'março', 4: 'abril',
            5: 'maio', 6: 'junho', 7: 'julho', 8: 'agosto',
            9: 'setembro', 10: 'outubro', 11: 'novembro', 12: 'dezembro'
        }
        data_formatada = f"São Paulo, {data_atual.day} de {meses.get(data_atual.month, '')} de {data_atual.year}"
        local_data_para = Paragraph(data_formatada, right_aligned_style)
        
        local_data_width, local_data_h = local_data_para.wrapOn(p, content_width, page_height)
        
        local_data_para.drawOn(p, page_width - margem_direita - local_data_width, current_y - local_data_h) 
        current_y -= local_data_h + 0.5 * cm # Espaço após data

        # Detalhes do Contrato
        valor_formatado_br = "R$ {:,.2f}".format(contrato.valor_contrato).replace(",", "X").replace(".", ",").replace("X", ".")

        tipo_indice_do_banco = contrato.tipo_indice
        indice_para_exibir = "Não Informado"
        if tipo_indice_do_banco:
            valor_normalizado = tipo_indice_do_banco.strip().upper()
            if valor_normalizado == 'IPCA':
                indice_para_exibir = 'IPCA (Índice Nacional de Preços ao Consumidor Amplo)'
            elif valor_normalizado == 'IGPM':
                indice_para_exibir = 'IGPM (Índice Geral de Preços do Mercado)'
            else:
                indice_para_exibir = f"{tipo_indice_do_banco} (Outro Índice)"

        data_inicio_obj = None 
        if isinstance(contrato.inicio_contrato, str):
            try:
                data_inicio_obj = datetime.strptime(contrato.inicio_contrato, '%Y-%m-%d').date()
            except ValueError:
                data_inicio_obj = None 
        else:
            data_inicio_obj = contrato.inicio_contrato

        inicio_contrato_str = data_inicio_obj.strftime('%d/%m/%Y') if data_inicio_obj else 'Data de Início Inválida'

        data_termino_obj = None
        if contrato.termino_contrato:
            if isinstance(contrato.termino_contrato, str):
                try:
                    data_termino_obj = datetime.strptime(contrato.termino_contrato, '%Y-%m-%d').date()
                except ValueError:
                    data_termino_obj = None
            else:
                data_termino_obj = contrato.termino_contrato

        termino_contrato_str = data_termino_obj.strftime('%d/%m/%Y') if data_termino_obj else 'Não definido'


        contrato_details = [
            f"<b>Nome:</b> {contrato.nome}",
            f"<b>CNPJ:</b> {contrato.cnpj}",
            f"<b>Endereço:</b> {contrato.endereco}",
            f"<b>CEP:</b> {contrato.cep}",
            f"<b>Estado:</b> {contrato.estado}",
            f"<b>Telefone:</b> {contrato.telefone}",
            f"<b>Email:</b> {contrato.email}",
            f"<b>Valor do Contrato:</b> {valor_formatado_br}",
            f"<b>Início do Contrato:</b> {inicio_contrato_str}",
            f"<b>Término do Contrato:</b> {termino_contrato_str}",
            f"<b>Abrangência do Contrato:</b> {contrato.abrangencia_contrato}",
            f"<b>Tipo de Índice de Reajuste:</b> {indice_para_exibir}",
        ]

        # Desenha os detalhes do contrato, verificando quebra de página
        for detail_text in contrato_details:
            para = Paragraph(detail_text, bold_style)
            _, para_h = para.wrapOn(p, content_width, page_height)
            
            if current_y - para_h - 0.2 * cm < margem_inferior + (4 * cm): # 4 cm para o rodapé e assinaturas
                p.showPage()
                current_y = page_height - margem_superior 
                
            para.drawOn(p, margem_esquerda, current_y - para_h)
            current_y -= (para_h + 0.2 * cm) # Desce a posição Y para o próximo parágrafo

        # --- Seção de Acordo e Assinaturas ---
        # Garante que as assinaturas tenham espaço suficiente
        if current_y - (2 * cm + 4 * cm + 2 * cm) < margem_inferior: 
            p.showPage()
            current_y = page_height - margem_superior

        agreement_para = Paragraph("Li e concordo com os termos do contrato.", normal_style)
        _, agreement_h = agreement_para.wrapOn(p, content_width, page_height)
        agreement_para.drawOn(p, margem_esquerda, current_y - agreement_h - 1 * cm) 
        current_y -= (agreement_h + 1 * cm)

        # Posição Y para as linhas de assinatura (abaixo do texto de acordo)
        y_line_position_signature = current_y - 2 * cm 

        # Largura da linha de assinatura
        signature_line_length = 6 * cm 

        # Espaçamento para o texto abaixo da linha
        gap_below_line = 0.2 * cm 

        # --- Assinatura Empresa (Esquerda) ---
        x_empresa_line_start = margem_esquerda + (content_width / 4) - (signature_line_length / 2) 
        p.line(x_empresa_line_start, y_line_position_signature, x_empresa_line_start + signature_line_length, y_line_position_signature)
        
        empresa_label_text = "Assinatura Empresa"
        empresa_label_para = Paragraph(empresa_label_text, centered_style)
        empresa_label_width, empresa_label_h = empresa_label_para.wrapOn(p, signature_line_length, page_height)
        
        empresa_label_x = x_empresa_line_start + (signature_line_length - empresa_label_width) / 2
        empresa_label_y = y_line_position_signature - empresa_label_h - gap_below_line
        
        empresa_label_para.drawOn(p, empresa_label_x, empresa_label_y)

        # --- Assinatura Contratante (Direita) ---
        x_contratante_line_start = margem_esquerda + (content_width * 3 / 4) - (signature_line_length / 2) 
        p.line(x_contratante_line_start, y_line_position_signature, x_contratante_line_start + signature_line_length, y_line_position_signature)
        
        # 1. Nome do Contratante (abaixo da linha)
        contratante_nome_text = contrato.nome
        contratante_nome_para = Paragraph(contratante_nome_text, centered_style)
        contratante_nome_width, contratante_nome_h = contratante_nome_para.wrapOn(p, signature_line_length, page_height)
        
        contratante_nome_x = x_contratante_line_start + (signature_line_length - contratante_nome_width) / 2
        contratante_nome_y = y_line_position_signature - contratante_nome_h - gap_below_line
        
        contratante_nome_para.drawOn(p, contratante_nome_x, contratante_nome_y)

        # 2. Texto "Assinatura Contratante" (abaixo do nome)
        contratante_label_text = "Assinatura Contratante"
        contratante_label_para = Paragraph(contratante_label_text, centered_style)
        contratante_label_width, contratante_label_h = contratante_label_para.wrapOn(p, signature_line_length, page_height)
        
        contratante_label_x = x_contratante_line_start + (signature_line_length - contratante_label_width) / 2
        contratante_label_y = contratante_nome_y - contratante_label_h - gap_below_line 
        
        contratante_label_para.drawOn(p, contratante_label_x, contratante_label_y)

        # --- Rodapé ---
        # O rodapé deve ser desenhado na margem inferior da PÁGINA ATUAL, não dependendo de current_y
        footer_text_content = f"M.A. Automatização - {contrato.endereco}, {contrato.cep}, {contrato.estado} | Telefone: {contrato.telefone} | Email: {contrato.email}"
        footer_para = Paragraph(footer_text_content, footer_style)
        
        footer_width, footer_h = footer_para.wrapOn(p, content_width, page_height)
        
        footer_x_center = margem_esquerda + (content_width - footer_width) / 2 
        
        footer_para.drawOn(p, footer_x_center, margem_inferior - (0.5 * cm) ) 

        # Finaliza e salva o PDF
        p.showPage() 
        p.save()

        output.seek(0)
        return send_file(output, as_attachment=True, download_name=f"contrato_{contrato.nome.replace(' ', '_')}.pdf", mimetype='application/pdf')

    except Exception as e:
        print(f'Erro ao gerar o PDF: {e}') 
        flash(f'Erro ao gerar o PDF: {e}', 'danger')
        return redirect(url_for('index'))
    
@app.route('/download_contrato_pdf/<int:id>')
@login_required
def download_contrato_pdf(id):
    contrato = ContratCond.query.get_or_404(id)

    # 1. Criar um buffer em memória para o PDF
    buffer = io.BytesIO()

    # 2. Configurar o documento PDF
    doc = SimpleDocTemplate(buffer, pagesize=letter)
    styles = getSampleStyleSheet()
    story = []

    # Estilo para o título
    style_title = styles['h1']
    style_title.alignment = TA_CENTER
    style_title.fontName = 'Arial-Bold' # Usando a fonte registrada

    # Estilo para o corpo do texto
    style_body = styles['Normal']
    style_body.fontName = 'Arial' # Usando a fonte registrada
    style_body.fontSize = 12
    style_body.leading = 14 # Espaçamento entre linhas

    # 3. Adicionar conteúdo ao PDF usando os dados do contrato
    story.append(Paragraph("TERMO DE CONTRATO DE SERVIÇOS", style_title))
    story.append(Spacer(1, 0.2 * inch)) # Espaço

    story.append(Paragraph(f"<b>NOME DO CONTRATANTE:</b> {contrato.nome}", style_body))
    story.append(Paragraph(f"<b>CNPJ:</b> {contrato.cnpj}", style_body))
    story.append(Paragraph(f"<b>ENDEREÇO:</b> {contrato.endereco}, CEP: {contrato.cep}", style_body))
    story.append(Paragraph(f"<b>ESTADO:</b> {contrato.estado}", style_body))
    story.append(Paragraph(f"<b>TELEFONE:</b> {contrato.telefone}", style_body))
    story.append(Paragraph(f"<b>E-MAIL:</b> {contrato.email}", style_body))
    story.append(Spacer(1, 0.2 * inch))

    # Formatação do valor do contrato para exibição no PDF
    # Certifique-se que contrato.valor_contrato é um Decimal ou float
    valor_formatado = "R$ {:,.2f}".format(contrato.valor_contrato).replace(",", "X").replace(".", ",").replace("X", ".")
    story.append(Paragraph(f"<b>VALOR DO CONTRATO:</b> {valor_formatado}", style_body))
    story.append(Paragraph(f"<b>INÍCIO DO CONTRATO:</b> {contrato.inicio_contrato.strftime('%d/%m/%Y')}", style_body))
    if contrato.termino_contrato: # Verifica se a data de término existe
        story.append(Paragraph(f"<b>TÉRMINO DO CONTRATO:</b> {contrato.termino_contrato.strftime('%d/%m/%Y')}", style_body))
    story.append(Paragraph(f"<b>ABRANGÊNCIA:</b> {contrato.abrangencia_contrato}", style_body))
    story.append(Paragraph(f"<b>TIPO DE ÍNDICE DE REAJUSTE:</b> {contrato.tipo_indice}", style_body))
    story.append(Spacer(1, 0.5 * inch))
    story.append(Paragraph(f"Este contrato foi gerado em: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}", styles['Italic']))

    # 4. Construir o PDF
    try:
        doc.build(story)
        buffer.seek(0) # Volta o ponteiro para o início do buffer

        # 5. Enviar o arquivo para o navegador
        return send_file(buffer, as_attachment=True, download_name=f"contrato_{contrato.nome.replace(' ', '_')}.pdf", mimetype='application/pdf')
    except Exception as e:
        flash(f"Erro ao gerar o PDF: {e}", "danger")
        # Se der erro, redireciona para a página de onde veio
        return redirect(url_for('index')) # Ou para a página de detalhes do contrato


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
        flash(f'Erro ao excluir contrato: {e}', 'error')
    return redirect(url_for('index'))

@app.route('/clausulas')
@login_required
def clausulas():
    clausulas_contrato = """
    <h2>Cláusulas Gerais do Contrato</h2>
    <ol>
        <li><b>Cláusula Primeira: Objeto do Contrato</b><br>
            Este contrato tem como objeto a prestação de serviços de [descrição dos serviços] pela [Nome da sua Empresa] para [Nome do Cliente], conforme as condições estabelecidas neste instrumento.
        </li>
        <li><b>Cláusula Segunda: Prazo</b><br>
            O presente contrato terá vigência a partir de [data de início] até [data de término], podendo ser renovado mediante acordo escrito entre as partes.
        </li>
        <li><b>Cláusula Terceira: Valor e Forma de Pagamento</b><br>
            O valor total do contrato é de R$ [valor], a ser pago da seguinte forma: [forma de pagamento].
        </li>
        <li><b>Cláusula Quarta: Obrigações das Partes</b><br>
            <ul>
                <li><b>4.1. Obrigações da [Nome da sua Empresa]:</b> [listar obrigações]</li>
                <li><b>4.2. Obrigações do [Nome do Cliente]:</b> [listar obrigações]</li>
            </ul>
        </li>
        <li><b>Cláusula Quinta: Rescisão</b><br>
            O presente contrato poderá ser rescindido por qualquer das partes, mediante notificação prévia de [número] dias, nos casos de [condições de rescisão].
        </li>
        <li><b>Cláusula Sexta: Foro</b><br>
            Fica eleito o foro da comarca de [cidade] - [estado] para dirimir quaisquer dúvidas ou litígios oriundos do presente contrato, renunciando as partes a qualquer outro, por mais privilegiado que seja.
        </li>
    </ol>
    """
    return render_template('clausulas.html', clausulas=clausulas_contrato)

if __name__ == '__main__':
    app.run(debug=True)