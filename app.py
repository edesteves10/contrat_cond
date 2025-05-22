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
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch, cm
from PIL import Image as PIL_Image
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT # TA_LEFT já está aqui, vamos usar
from reportlab.platypus import Paragraph, Spacer, Image
from reportlab.pdfbase import pdfmetrics as pdfmetrics_base
from reportlab.pdfbase.ttfonts import TTFont
from flask import jsonify

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
            fontName='Arial' # Usar Arial normal para centralizado
        )
        centered_bold_style = ParagraphStyle(
            name='CenteredBold',
            parent=centered_style,
            fontName='Arial-Bold',
            fontSize=15,
            spaceAfter=0.05 * cm # Reduzir ainda mais o espaço abaixo do título da empresa
        )
        cnpj_style = ParagraphStyle(
            name='CNPJStyle',
            parent=centered_style,
            fontSize=10,
            spaceAfter=0.4 * cm # Reduzir um pouco o espaço abaixo do CNPJ
        )
        footer_style = ParagraphStyle(
            name='Footer',
            fontName='Arial',
            fontSize=10,
            alignment=TA_CENTER
        )
        section_title_style = ParagraphStyle(
            name='SectionTitle',
            parent=centered_style,
            fontName='Arial-Bold',
            fontSize=14,
            spaceAfter=0.5 * cm
        )

        # --- Cabeçalho ---
        logo_path = os.path.join(app.root_path, 'static', 'logo.png')
        logo_width = 3.5 * cm # Largura desejada para o logo
        logo_height = 0 # Inicializado, será calculado pela proporção
        
        # Posição Y para o topo da área do cabeçalho
        header_top_y = page_height - margem_superior
        
        # Variável para rastrear a posição Y mais baixa ocupada pelo cabeçalho
        lowest_header_element_y = header_top_y # Começa no topo e desce

        # 1. Tentar carregar e posicionar o logo
        logo_x = margem_esquerda
        logo_y = header_top_y # Posição inicial para o logo (será ajustada após calcular a altura)

        try:
            img = PIL_Image.open(logo_path)
            img_width_orig, img_height_orig = img.size
            aspect_ratio = img_height_orig / img_width_orig
            logo_height = logo_width * aspect_ratio

            logo_y = header_top_y - logo_height # Posição Y do canto inferior esquerdo do logo
            logo = Image(logo_path, width=logo_width, height=logo_height)
            logo.drawOn(p, logo_x, logo_y)
            lowest_header_element_y = min(lowest_header_element_y, logo_y) # Atualiza a posição mais baixa
        except FileNotFoundError:
            print(f"Erro: Logo não encontrado em {logo_path}")
            logo_height = 0 # Se o logo não existe, sua altura é 0 para o layout
            # Se não houver logo, o texto começará na margem esquerda sem deslocamento do logo.

        # 2. Preparar e posicionar o texto (Nome da Empresa e CNPJ)
        # Para centralizar no cabeçalho inteiro, a área de texto começa na margem esquerda e vai até a margem direita.
        text_area_x_start_full_width = margem_esquerda
        text_area_width_full_width = page_width - margem_esquerda - margem_direita

        empresa_nome_para = Paragraph("M.A. Automatização", centered_bold_style)
        cnpj_para = Paragraph("CNPJ: 27.857.310/0001-83", centered_style)

        # Medir a altura dos parágrafos de texto (usando a largura total do cabeçalho)
        _, empresa_nome_height = empresa_nome_para.wrapOn(p, text_area_width_full_width, page_height)
        _, cnpj_height = cnpj_para.wrapOn(p, text_area_width_full_width, page_height)

        text_block_gap = 0.2 * cm # Espaço entre o nome da empresa e o CNPJ
        total_text_block_height = empresa_nome_height + cnpj_height + text_block_gap

        # Calcular a posição vertical para centralizar o bloco de texto com a altura do logo
        if logo_height > 0:
            # Centro Y do logo
            logo_center_y = logo_y + (logo_height / 2)
            # Topo Y do bloco de texto para centralizá-lo com o logo
            text_block_top_y = logo_center_y + (total_text_block_height / 2)
        else:
            # Se não há logo, simplesmente posicione o texto a partir da margem superior
            text_block_top_y = header_top_y # Usar header_top_y, que é page_height - margem_superior

        # Posição Y do nome da empresa
        empresa_nome_y = text_block_top_y - empresa_nome_height
        # Posição Y do CNPJ (abaixo do nome da empresa)
        cnpj_y = empresa_nome_y - cnpj_height - text_block_gap

        # Calcular posição X para centralizar o texto dentro da área de texto *total* do cabeçalho
        empresa_nome_x = text_area_x_start_full_width + (text_area_width_full_width - empresa_nome_para.wrapOn(p, text_area_width_full_width, page_height)[0]) / 2
        cnpj_x = text_area_x_start_full_width + (text_area_width_full_width - cnpj_para.wrapOn(p, text_area_width_full_width, page_height)[0]) / 2

        # Desenhar os parágrafos de texto
        empresa_nome_para.drawOn(p, empresa_nome_x, empresa_nome_y)
        cnpj_para.drawOn(p, cnpj_x, cnpj_y)

        # 3. Desenhar a linha divisória do cabeçalho
        calculated_lowest_text_y = cnpj_y - cnpj_height # Fundo do CNPJ
        
        # Considera o menor ponto entre o logo e o texto para a linha
        line_y_position = min(lowest_header_element_y, calculated_lowest_text_y) - 0.5 * cm # 0.5 cm de espaço após o cabeçalho

        # A linha deve ir de margem_esquerda a margem_direita
        p.line(margem_esquerda, line_y_position, page_width - margem_direita, line_y_position)

        # --- Fim do Cabeçalho ---

        # 4. Inserir "Informações do Contrato" centralizado
        # Definir a largura total de texto utilizável para o corpo do contrato
        texto_width = page_width - margem_esquerda - margem_direita
        
        section_title = Paragraph("Informações do Contrato", section_title_style)
        section_title_width, section_title_height = section_title.wrapOn(p, texto_width, page_height)
        section_title_x = margem_esquerda + (texto_width - section_title_width) / 2
        
        # Posição Y para o título da seção, logo abaixo da linha do cabeçalho
        y_position = line_y_position - 0.5 * cm # 0.5 cm de espaço após a linha do cabeçalho
        section_title.drawOn(p, section_title_x, y_position - section_title_height)
        y_position -= section_title_height + 0.5 * cm # Ajusta y_position para o conteúdo abaixo

        # --- Conteúdo do contrato (continua aqui, usando a nova y_position) ---
        conteudo_formatado = [
            Paragraph(f"<b>Nome:</b> {contrato.nome}", bold_style),
            Paragraph(f"<b>CNPJ:</b> {contrato.cnpj}", bold_style),
            Paragraph(f"<b>Endereço:</b> {contrato.endereco}", bold_style),
            Paragraph(f"<b>CEP:</b> {contrato.cep}", bold_style),
            Paragraph(f"<b>Estado:</b> {contrato.estado}", bold_style),
            Paragraph(f"<b>Telefone:</b> {contrato.telefone}", bold_style),
            Paragraph(f"<b>Email:</b> {contrato.email}", bold_style),
            Paragraph(f"<b>Valor do Contrato:</b> R$ {contrato.valor_contrato:.2f}", bold_style),
            Paragraph(f"<b>Início do Contrato:</b> {contrato.inicio_contrato}", bold_style),
            Paragraph(f"<b>Término do Contrato:</b> {contrato.termino_contrato if contrato.termino_contrato else 'Não definido'}", bold_style),
            Paragraph(f"<b>Abrangência do Contrato:</b> {contrato.abrangencia_contrato}", bold_style),
        ]

        x_position = margem_esquerda
        for item in conteudo_formatado:
            item_width, item_height = item.wrapOn(p, texto_width, page_height)
            # Verificar se há espaço suficiente para o próximo item
            if y_position - item_height - 0.2 * cm < margem_inferior + 2*cm: # Ajuste de 2cm para não sobrepor o rodapé e a linha de assinatura
                p.showPage() # Adiciona nova página
                # Se desejar repetir o cabeçalho na nova página, você precisaria de uma função separada para desenhá-lo aqui.
                # Por simplicidade, apenas reiniciamos o y_position para o topo.
                y_position = page_height - margem_superior # Reinicia Y no topo da nova página
            
            item.drawOn(p, x_position, y_position - item_height)
            y_position -= item_height + 0.2 * cm # Adiciona um pequeno espaço entre os itens

        # --- NOVAS SEÇÕES: ACORDO E ASSINATURAS ---

        # Definir novos estilos para o texto de acordo e rótulos de assinatura
        agreement_style = ParagraphStyle(
            name='AgreementText',
            parent=normal_style,
            fontSize=10,
            alignment=TA_LEFT, # <<-- ALTERADO PARA TA_LEFT
            spaceAfter=0.5 * cm # Espaço após o texto de acordo
        )
        signature_label_style = ParagraphStyle(
            name='SignatureLabel',
            parent=normal_style,
            fontSize=10,
            alignment=TA_CENTER,
        )

        # ADICIONE AQUI O CÓDIGO PARA O RODAPÉ (ANTES DAS ASSINATURAS)
        footer_text_content = "M.A. Automatização - "
        footer_text_content += f"{contrato.endereco}, {contrato.cep}, {contrato.estado} | Telefone: {contrato.telefone} | Email: {contrato.email}"
        footer_text = Paragraph(footer_text_content, footer_style)
        footer_width, footer_height = footer_text.wrapOn(p, texto_width, page_height)
        footer_x = margem_esquerda + (texto_width - footer_width) / 2
        footer_y = margem_inferior


        # Calcular a posição para o topo do rodapé (considerando que o rodapé já foi definido)
        y_footer_top = footer_y + footer_height

        # Posição inicial para a seção de assinaturas (acima do rodapé)
        y_signatures_start = y_footer_top + 4 * cm # 4 cm acima do rodapé (ajuste conforme necessário)

        # Texto "Li e concordo com os termos do contrato."
        agreement_paragraph = Paragraph("Li e concordo com os termos do contrato.", agreement_style)
        agreement_width, agreement_height = agreement_paragraph.wrapOn(p, texto_width, page_height)
        agreement_x = margem_esquerda # <<-- ALTERADO PARA ALINHAR À ESQUERDA
        agreement_paragraph.drawOn(p, agreement_x, y_signatures_start)

        # Posição para as linhas de assinatura (abaixo do texto de acordo)
        y_line_position_signature = y_signatures_start - agreement_height - 1.5 * cm # 1.5 cm abaixo do texto de acordo

        # Largura da linha de assinatura
        signature_line_length = 6 * cm # 6 cm para cada linha

        # Assinatura Empresa (Esquerda)
        x_empresa_line = margem_esquerda + (texto_width / 4) - (signature_line_length / 2)
        p.line(x_empresa_line, y_line_position_signature, x_empresa_line + signature_line_length, y_line_position_signature)
        empresa_label = Paragraph("Assinatura Empresa", signature_label_style)
        empresa_label_width, empresa_label_height = empresa_label.wrapOn(p, signature_line_length, page_height)
        empresa_label.drawOn(p, x_empresa_line + (signature_line_length - empresa_label_width) / 2, y_line_position_signature - empresa_label_height - 0.2 * cm)

        # Assinatura Contratante (Direita)
        x_contratante_line = margem_esquerda + (texto_width * 3 / 4) - (signature_line_length / 2)
        p.line(x_contratante_line, y_line_position_signature, x_contratante_line + signature_line_length, y_line_position_signature)
        contratante_label = Paragraph(f"Assinatura Contratante", signature_label_style)
        contratante_label_width, contratante_label_height = contratante_label.wrapOn(p, signature_line_length, page_height)
        contratante_label.drawOn(p, x_contratante_line + (signature_line_length - contratante_label_width) / 2, y_line_position_signature - contratante_label_height - 0.2 * cm)

        # --- Rodapé (Centralizado, Arial tamanho 10, na margem inferior) ---
        footer_text.drawOn(p, footer_x, footer_y)

        p.save()
        output.seek(0)
        return send_file(output, as_attachment=True, download_name=f"contrato_{contrato.id}.pdf", mimetype='application/pdf')
    except Exception as e:
        print(f'Erro ao gerar PDF (ABNT) no try-except: {e}')
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