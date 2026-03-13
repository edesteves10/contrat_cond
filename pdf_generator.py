# pdf_generator.py (Função gerar_pdf_reportlab)

from io import BytesIO
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import Paragraph
from reportlab.lib.units import inch
from reportlab.lib import colors
import datetime
import os 
# Funções format_currency_br e format_date_br devem estar aqui, logo acima de gerar_pdf_reportlab
# pdf_generator.py (Após os imports e ANTES de gerar_pdf_reportlab)

# --- CONFIGURAÇÃO DE ESTILOS E FUNÇÕES DE AJUDA ---

def format_currency_br(value):
    """Formata valor float/Decimal para o formato R$ X.XXX,XX"""
    try:
        val = float(value) 
        return f'R$ {val:,.2f}'.replace(',', 'X').replace('.', ',').replace('X', '.')
    except:
        return 'R$ 0,00'

def format_date_br(date_obj, include_day=True):
    """Formata objeto datetime.date para DD de MÊS de AAAA ou MÊS de AAAA."""
    import datetime
    
    nomes_meses = {
        1: 'janeiro', 2: 'fevereiro', 3: 'março', 4: 'abril', 5: 'maio', 6: 'junho',
        7: 'julho', 8: 'agosto', 9: 'setembro', 10: 'outubro', 11: 'novembro', 12: 'dezembro'
    }

    data_formatada = None
    
    if isinstance(date_obj, datetime.date):
        data_formatada = date_obj
    elif date_obj and isinstance(date_obj, str):
        try:
            # Tenta converter do formato 'YYYY-MM-DD' (padrão HTML)
            data_formatada = datetime.datetime.strptime(date_obj, '%Y-%m-%d').date()
        except ValueError:
            # Tenta converter do formato 'DD/MM/AAAA' (caso a data já venha formatada)
            try:
                data_formatada = datetime.datetime.strptime(date_obj, '%d/%m/%Y').date()
            except ValueError:
                return date_obj # Retorna a string original se a conversão falhar

    if data_formatada:
        mes_extenso = nomes_meses.get(data_formatada.month, str(data_formatada.month))
        if include_day:
            return f"{data_formatada.day} de {mes_extenso} de {data_formatada.year}"
        else:
            return f"{mes_extenso} de {data_formatada.year}"
    
    return 'N/A'
    
# --- FUNÇÃO PRINCIPAL QUE GERA O PDF (def gerar_pdf_reportlab(data):) segue abaixo ---
def gerar_pdf_reportlab(data):
    buffer = BytesIO()
    p = canvas.Canvas(buffer, pagesize=letter)
    width, height = letter # 612x792 pontos
    margin = 50
    line_height = 15
    
    # ------------------ 0. DEFINIÇÃO DE ESTILOS E SETUP ------------------
    
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name='TitleStyle', fontSize=14, fontName='Helvetica-Bold', alignment=1))
    styles.add(ParagraphStyle(name='MyBodyTextBold', fontSize=10, fontName='Helvetica-Bold'))
    styles.add(ParagraphStyle(name='MyBodyText', fontSize=10, fontName='Helvetica'))
    styles.add(ParagraphStyle(name='Rodape', fontSize=8, fontName='Helvetica', alignment=1))
    
    # ------------------ 1. CABEÇALHO (Logo e Info da Empresa) ------------------
    
    # Y da linha divisória (Ajustado para height - 90)
    text_y_separator = height - 90 
    logo_y = height - 85 
    
    logo_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static', 'logo.png')
    if os.path.exists(logo_path):
        p.drawImage(logo_path, 
                    x=margin,              
                    y=logo_y,         
                    width=60,              
                    height=60,
                    mask='auto')
        text_x_start = margin + 75 
    else:
        text_x_start = margin 

    p.setFont('Helvetica-Bold', 12)
    p.drawString(text_x_start, height - 30, "M.A. Automação")
    p.setFont('Helvetica', 10)
    p.drawString(text_x_start, height - 45, "CNPJ: 27.857.310/0001-83")
    
    # Linha divisória abaixada.
    p.line(margin, text_y_separator, width - margin, text_y_separator) 

    # ------------------ 2. TÍTULO PRINCIPAL E DATA ------------------

    titulo = Paragraph("CONTRATO DE PRESTAÇÃO DE SERVIÇOS", styles['TitleStyle'])
    titulo.wrapOn(p, width - 2 * margin, 50)
    titulo.drawOn(p, margin, height - 110)
    
    # Data alinhada à direita e com mês por extenso
    p.setFont('Helvetica', 10)
    # data_hoje_extenso usa format_date_br com dia e mês por extenso
    data_hoje_extenso = format_date_br(datetime.date.today(), include_day=True)
    data_str = f"São Paulo, {data_hoje_extenso}" 
    
    p.drawString(width - margin - p.stringWidth(data_str, 'Helvetica', 10), height - 140, data_str) 
    
    y = height - 170 # Começa o bloco de dados

    # ------------------ 3. DADOS DO CONTRATANTE ------------------
    
    y_gap = 160 
    
    # Lógica para garantir que o valor não seja uma string vazia ('')
    indice_reajuste_valor = data.get('tipo_indice')
    if not indice_reajuste_valor:
        indice_reajuste_valor = 'N/A'
    
    campos_principais = [
        ("Nome:", data.get('nome', 'N/A')),
        ("CNPJ:", data.get('cnpj', 'N/A')),
        ("Telefone:", data.get('telefone', 'N/A')),
        ("Email:", data.get('email', 'N/A')),
        ("Valor do Contrato:", format_currency_br(data.get('valor_contrato', 0))),
        # Formata as datas com mês por extenso
        ("Início do Contrato:", format_date_br(data.get('inicio_contrato'), include_day=True)),
        ("Término do Contrato:", format_date_br(data.get('termino_contrato'), include_day=True) or 'Indeterminado'),
        ("Abrangência do Contrato:", data.get('abrangencia_contrato', 'N/A')),
        ("Tipo de Índice de Reajuste:", indice_reajuste_valor) # Usa a variável verificada
    ]
    
    # Loop para desenhar os campos principais
    for label, value in campos_principais:
        p.setFont('Helvetica-Bold', 10)
        p.drawString(margin, y, label)
        p.setFont('Helvetica', 10)
        p.drawString(margin + y_gap, y, value) 
        y -= line_height

    # ----------------- Endereço Completo -----------------
    y -= line_height # Espaço extra
    
    p.setFont('Helvetica-Bold', 10)
    p.drawString(margin, y, "Endereço Completo:")
    y -= line_height

    # Linha com Rua/Cidade/Estado
    p.setFont('Helvetica', 10)
    endereco_str = f"Rua: {data.get('endereco', 'N/A')}, {data.get('cidade', 'São Paulo')} - {data.get('estado', 'SP')}"
    p.drawString(margin, y, endereco_str)
    y -= line_height

    # Linha com CEP
    cep_str = f"CEP: {data.get('cep', 'N/A')}"
    p.drawString(margin, y, cep_str)
    y -= line_height * 3 # Espaço para o bloco 4

    # ------------------ 4. CLÁUSULAS (Frase Simples) ------------------
    
    confirmacao_texto = "Li e concordo com os termos e condições."
    confirmacao = Paragraph(confirmacao_texto, styles['MyBodyText'])
    
    confirmacao.wrapOn(p, width - 2 * margin, 20)
    confirmacao.drawOn(p, margin, y - confirmacao.height)
    y -= confirmacao.height + (line_height * 4) 
    
    # ------------------ 5. RODAPÉ E ASSINATURAS ------------------
    
    y_assinaturas = 150 
    y_text = y_assinaturas - 15

    # Assinatura da Empresa (Esquerda)
    p.line(margin + 20, y_assinaturas, margin + 220, y_assinaturas)
    p.setFont('Helvetica', 10)
    p.drawString(margin + 40, y_text, "Assinatura Empresa (M.A. Automação)")

    # Assinatura do Contratante (Direita)
    p.line(width - 270, y_assinaturas, width - 70, y_assinaturas)
    
    # Nome do Contratante em negrito
    p.setFont('Helvetica-Bold', 10)
    p.drawString(width - 270, y_text, f"{data.get('nome', 'N/A')}")
    
    p.setFont('Helvetica', 10)
    p.drawString(width - 270, y_text - 15, "Assinatura Contratante")
    p.drawString(width - 270, y_text - 30, f"CNPJ: {data.get('cnpj', 'N/A')}") 
    
    # Rodapé de Contato da Empresa (Fixo e Limpo)
    rodape_texto = f"Rua: {data.get('endereco', 'Rua Exemplo')} - {data.get('cidade', 'São Paulo')} - {data.get('estado', 'SP')} - CEP: {data.get('cep', '00000-000')} | Tel: {data.get('telefone', '(11) 2628-3586')}"
    rodape = Paragraph(rodape_texto, styles['Rodape'])
    
    rodape.wrapOn(p, width - 2 * margin, 15)
    rodape.drawOn(p, margin, 20) 


    p.showPage()
    p.save()
    
    buffer.seek(0)
    return buffer