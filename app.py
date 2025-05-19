import os
import datetime
import sqlite3
from flask import Flask, render_template, request, redirect, url_for, send_file, flash, session
from flask_sqlalchemy import SQLAlchemy
from reportlab.pdfgen import canvas
from io import BytesIO
import re
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch, cm # Adicione cm aqui se não estiver
from PIL import Image as PIL_Image
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.platypus import Paragraph, Spacer, Image # 'Image' aqui é do reportlab
#from reportlab.lib.fonts import pdfmetrics
#from reportlab.lib.fonts import registerFont
from reportlab.pdfbase import pdfmetrics as pdfmetrics_base
# REMOVA ESTA LINHA: from reportlab.pdfbase import pdfbase
from reportlab.pdfbase import pdfdoc
from reportlab.pdfbase.ttfonts import TTFont

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
    id = db.Column(db.Integer, primary_key=True)
    created = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    nome = db.Column(db.String(200), nullable=False)
    cnpj = db.Column(db.String(14), unique=True, nullable=False)
    endereco = db.Column(db.String(200), nullable=False)
    cep = db.Column(db.String(200), nullable=False)
    estado = db.Column(db.String(200), nullable=False)
    telefone = db.Column(db.String(200), nullable=False)
    email = db.Column(db.String(200), nullable=False)
    valor_contrato = db.Column(db.Float, nullable=False)
    inicio_contrato = db.Column(db.String(200), nullable=False)
    termino_contrato = db.Column(db.String(200))
    abrangencia_contrato = db.Column(db.String(200), nullable=False)

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
    if request.method == 'POST':
        try:
            nome = request.form['nome']
            cnpj = request.form['cnpj']
            endereco = request.form['endereco']
            cep = request.form['cep']
            estado = request.form['estado']
            telefone = request.form['telefone']
            email = request.form['email']
            valor_contrato_str = request.form['valor_contrato']
            inicio_contrato = request.form['inicio_contrato']
            termino_contrato = request.form.get('termino_contrato') or None
            abrangencia_contrato = request.form['abrangencia_contrato']

            try:
                valor_contrato = float(valor_contrato_str)
                novo_contrato = ContratCond(nome=nome, cnpj=cnpj, endereco=endereco, cep=cep, estado=estado, telefone=telefone, email=email, valor_contrato=valor_contrato, inicio_contrato=inicio_contrato, termino_contrato=termino_contrato, abrangencia_contrato=abrangencia_contrato)
                db.session.add(novo_contrato)
                db.session.commit()
                flash('Contrato adicionado com sucesso!', 'success')
                return redirect(url_for('index'))
            except ValueError:
                flash('Valor do contrato inválido.', 'error')
            except Exception as e:
                db.session.rollback()
                flash(f'Erro ao adicionar contrato: {e}', 'error')
        except KeyError as e:
            flash(f'Campo obrigatório ausente: {e}', 'error')
        except Exception as e:
            flash(f'Ocorreu um erro ao processar o formulário: {e}', 'error')

    page = request.args.get('page', 1, type=int)
    contratos = ContratCond.query.paginate(page=page, per_page=10)
    return render_template('index.html', contratos=contratos)

@app.route('/edit/<int:id>', methods=['GET', 'POST'])
@login_required
def edit(id):
    contrato = ContratCond.query.get_or_404(id)
    if request.method == 'POST':
        try:
            contrato.nome = request.form['nome']
            contrato.cnpj = request.form['cnpj']
            contrato.endereco = request.form['endereco']
            contrato.cep = request.form['cep']
            contrato.estado = request.form['estado']
            contrato.telefone = request.form['telefone']
            contrato.email = request.form['email']
            valor_contrato_str = request.form['valor_contrato']
            contrato.inicio_contrato = request.form['inicio_contrato']
            contrato.termino_contrato = request.form.get('termino_contrato') or None
            contrato.abrangencia_contrato = request.form['abrangencia_contrato']

            try:
                contrato.valor_contrato = float(valor_contrato_str)
                db.session.commit()
                flash('Contrato atualizado com sucesso!', 'success')
                return redirect(url_for('index'))
            except ValueError:
                flash('Valor do contrato inválido.', 'error')
            except Exception as e:
                db.session.rollback()
                flash(f'Erro ao atualizar contrato: {e}', 'error')
        except KeyError as e:
            flash(f'Campo obrigatório ausente: {e}', 'error')
        except Exception as e:
            flash(f'Ocorreu um erro ao processar o formulário: {e}', 'error')
    return render_template('edit.html', contrato=contrato)


@app.route('/search', methods=['POST'])
@login_required
def search():
    query = request.form.get('query', '')
    try:
        contratos = ContratCond.query.filter(ContratCond.nome.ilike(f'%{query}%')).all()
        return render_template('index.html', contratos=contratos)
    except Exception as e:
        flash(f'Erro ao realizar a busca: {e}', 'error')
        return render_template('index.html', contratos=[])

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

@app.route('/pdf/<int:id>')
@login_required
def generate_pdf(id):
    contrato = ContratCond.query.get_or_404(id)
    try:
        output = BytesIO()
        # Definir margens em cm e converter para pontos
        margem_superior = 2 * cm
        margem_inferior = 2 * cm
        margem_esquerda = 2 * cm
        margem_direita = 2 * cm
        page_width, page_height = letter

        p = canvas.Canvas(output, pagesize=letter)

        styles = getSampleStyleSheet()
        normal_style = ParagraphStyle(
            name='Normal',
            fontName='Arial',
            fontSize=12,
            leading=1.5 * 12, # Espaçamento entre linhas de 1.5
            alignment=TA_LEFT,
            spaceAfter=0.2 * cm # Adicionar espaço após cada parágrafo
        )
        bold_style = ParagraphStyle(
            name='BoldStyle',
            parent=normal_style,
            fontName='Arial-Bold'
        )
        centered_style = ParagraphStyle(
            name='Centered',
            parent=normal_style,
            alignment=TA_CENTER,
            fontName='Arial' # Usar Arial normal para centralizado, negrito será aplicado se necessário
        )
        centered_bold_style = ParagraphStyle(
            name='CenteredBold',
            parent=centered_style,
            fontName='Arial-Bold',
            fontSize=15,
            spaceAfter=0.2 * cm # Adicionar espaço após o título
        )
        cnpj_style = ParagraphStyle(
            name='CNPJStyle',
            parent=centered_style,
            fontSize=10,
            spaceAfter=0.5 * cm # Adicionar espaço após o CNPJ
        )

        # --- Cabeçalho ---
        logo_path = os.path.join(app.root_path, 'static', 'logo.png')
        logo_width = 3 * cm
        logo_height = 0 # Inicializa a altura do logo

        # --- Cabeçalho ---
        logo_path = os.path.join(app.root_path, 'static', 'logo.png')
        logo_width = 3 * cm
        logo_height = 0 # Inicializa a altura do logo

        try:
            img = PIL_Image.open(logo_path)
            img_width, img_height = img.size
            aspect_ratio = img_height / img_width
            logo_height = logo_width * aspect_ratio
            logo = Image(logo_path, width=logo_width, height=logo_height)
            # Ajuste na posição Y do logo (subindo um pouco)
            logo.drawOn(p, margem_esquerda, page_height - margem_superior - logo_height + 0.2 * cm)
        except FileNotFoundError:
            print(f"Erro: Logo não encontrado em {logo_path}")

        # Largura disponível para o texto (aproximadamente)
        texto_width = page_width - margem_esquerda - margem_direita

        # Título da Empresa (Centralizado e em Negrito)
        empresa_nome = Paragraph("M.A. Automatização", centered_bold_style)
        empresa_nome_width, empresa_nome_height = empresa_nome.wrapOn(p, texto_width, page_height)

        # Calcular a posição X para centralizar o texto (considerando a margem esquerda)
        empresa_x = margem_esquerda + (texto_width - empresa_nome_width) / 2
        # Ajuste na posição Y do nome da empresa (subindo um pouco mais)
        empresa_y = page_height - margem_superior - logo_height - empresa_nome_height + 0.1 * cm

        empresa_nome.drawOn(p, empresa_x, empresa_y)

        # CNPJ (Centralizado)
        cnpj_text = Paragraph("CNPJ: 27.857.310/0001-83", cnpj_style)
        cnpj_width, cnpj_height = cnpj_text.wrapOn(p, texto_width, page_height)
        cnpj_x = margem_esquerda + (texto_width - cnpj_width) / 2
        # Ajuste na posição Y do CNPJ (subindo um pouco)
        cnpj_y = page_height - margem_superior - logo_height - empresa_nome_height - cnpj_height + 0.3 * cm

        cnpj_text.drawOn(p, cnpj_x, cnpj_y)

        p.line(margem_esquerda, cnpj_y - 0.3 * cm, page_width - margem_direita, cnpj_y - 0.3 * cm)

                    # --- Conteúdo do contrato ---
        y_position = page_height - margem_superior - logo_height - empresa_nome.height - cnpj_text.height - 1 * cm
        conteudo_formatado = [
            Paragraph(f"<b>Nome:</b> {contrato.nome}", bold_style),
            Paragraph(contrato.nome, normal_style),
            Paragraph(f"<b>CNPJ:</b> {contrato.cnpj}", bold_style),
            Paragraph(contrato.cnpj, normal_style),
            Paragraph(f"<b>Endereço:</b> {contrato.endereco}", bold_style),
            Paragraph(contrato.endereco, normal_style), # Linha corrigida com o fechamento do parêntese e vírgula
            Paragraph(f"<b>CEP:</b> {contrato.cep}", bold_style),
            Paragraph(contrato.cep, normal_style),
            Paragraph(f"<b>Estado:</b> {contrato.estado}", bold_style),
            Paragraph(contrato.estado, normal_style),
            Paragraph(f"<b>Telefone:</b> {contrato.telefone}", bold_style),
            Paragraph(contrato.telefone, normal_style),
            Paragraph(f"<b>Email:</b> {contrato.email}", bold_style),
            Paragraph(contrato.email, normal_style),
            Paragraph(f"<b>Valor do Contrato:</b> R$ {contrato.valor_contrato:.2f}", bold_style),
            Paragraph(f"R$ {contrato.valor_contrato:.2f}", normal_style),
            Paragraph(f"<b>Início do Contrato:</b> {contrato.inicio_contrato}", bold_style),
            Paragraph(contrato.inicio_contrato, normal_style),
            Paragraph(f"<b>Término do Contrato:</b> {contrato.termino_contrato if contrato.termino_contrato else 'Não definido'}", bold_style),
            Paragraph(contrato.termino_contrato if contrato.termino_contrato else 'Não definido', normal_style),
            Paragraph(f"<b>Abrangência do Contrato:</b> {contrato.abrangencia_contrato}", bold_style),
            Paragraph(contrato.abrangencia_contrato, normal_style),
        ]

        x_position = margem_esquerda
        for item in conteudo_formatado:
            item_width, item_height = item.wrapOn(p, page_width - margem_esquerda - margem_direita, page_height)
            item.drawOn(p, x_position, y_position - item_height)
            y_position -= item_height

        # --- Rodapé (Centralizado, Arial tamanho 10, na margem inferior) ---
        p.setFont("Arial", 10)
        footer_text = "Rua Giovanni Di Balduccio, 402, Bairro: Vila Moraes, CEP: 04170-000-SP, E-mail: m.a.automatizacao@gmail.com, Telefone(s): (11) 4645-4199, (11) 4018-3899."
        p.drawCentredString(page_width / 2, margem_inferior / 2, footer_text)

        p.save()
        output.seek(0)
        return send_file(output, as_attachment=True, download_name=f"contrato_{contrato.id}.pdf", mimetype='application/pdf')
    except Exception as e:
        flash(f'Erro ao gerar PDF (ABNT): {e}', 'error')
        return redirect(url_for('index'))

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