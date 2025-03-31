import os
import datetime
import sqlite3
from flask import Flask, render_template, request, redirect, url_for, send_file, flash
from flask_sqlalchemy import SQLAlchemy
from reportlab.pdfgen import canvas
from io import BytesIO
import re

project_dir = os.path.dirname(os.path.abspath(__file__))
database_file = "sqlite:///{}".format(os.path.join(project_dir, "database.db"))

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your secret key'
app.config['SQLALCHEMY_DATABASE_URI'] = database_file
db = SQLAlchemy(app)

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
    termino_contrato = db.Column(db.String(200), nullable=True)
    abrangencia_contrato = db.Column(db.String(200), nullable=False)

def validate_cnpj(cnpj):
    cnpj = re.sub(r'[^\d]', '', cnpj)
    if len(cnpj) != 14:
        return False
    return True

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        nome = request.form['nome']
        cnpj = request.form['cnpj']
        endereco = request.form['endereco']
        cep = request.form['cep']
        estado = request.form['estado']
        telefone = request.form['telefone']
        email = request.form['email']
        valor_contrato = request.form['valor_contrato']
        inicio_contrato = request.form['inicio_contrato']
        termino_contrato = request.form.get('termino_contrato')
        abrangencia_contrato = request.form['abrangencia_contrato']

        if not validate_cnpj(cnpj):
            flash('CNPJ inválido. Deve conter 14 dígitos numéricos.', 'error')
            return redirect(url_for('index'))

        if ContratCond.query.filter_by(cnpj=cnpj).first():
            flash('CNPJ já cadastrado.', 'error')
            return redirect(url_for('index'))

        if not abrangencia_contrato:
            flash('Abrangência do contrato é obrigatória.', 'error')
            return redirect(url_for('index'))

        contrato = ContratCond(nome=nome, cnpj=cnpj, endereco=endereco, cep=cep, estado=estado, telefone=telefone,
                               email=email, valor_contrato=valor_contrato, inicio_contrato=inicio_contrato,
                               termino_contrato=termino_contrato, abrangencia_contrato=abrangencia_contrato)
        db.session.add(contrato)
        db.session.commit()
        flash('Dados inseridos com sucesso!', 'success')
        return redirect(url_for('index'))

    contratos = ContratCond.query.all()
    return render_template('index.html', contratos=contratos)

@app.route('/edit/<int:id>', methods=['GET', 'POST'])
def edit(id):
    contrato = ContratCond.query.get(id)
    if request.method == 'POST':
        contrato.nome = request.form['nome']
        contrato.cnpj = request.form['cnpj']
        contrato.endereco = request.form['endereco']
        contrato.cep = request.form['cep']
        contrato.estado = request.form['estado']
        contrato.telefone = request.form['telefone']
        contrato.email = request.form['email']
        contrato.valor_contrato = request.form['valor_contrato']
        contrato.inicio_contrato = request.form['inicio_contrato']
        contrato.termino_contrato = request.form.get('termino_contrato')
        contrato.abrangencia_contrato = request.form['abrangencia_contrato']

        if not contrato.abrangencia_contrato:
            flash('Abrangência do contrato é obrigatória.', 'error')
            return redirect(url_for('edit', id=id))

        db.session.commit()
        flash('Dados editados com sucesso!', 'success')
        return redirect(url_for('index'))
    return render_template('edit.html', contrato=contrato)

@app.route('/pdf/<int:id>')
def generate_pdf(id):
    contrato = ContratCond.query.get(id)
    buffer = BytesIO()
    p = canvas.Canvas(buffer)
    p.drawString(100, 800, f"Nome: {contrato.nome}")
    p.drawString(100, 780, f"CNPJ: {contrato.cnpj}")
    p.drawString(100, 760, f"Endereço: {contrato.endereco}")
    p.drawString(100, 740, f"Início do Contrato: {contrato.inicio_contrato}")
    if contrato.termino_contrato:
        p.drawString(100, 720, f"Término do Contrato: {contrato.termino_contrato}")
    p.drawString(100, 700, f"Abrangência do Contrato: {contrato.abrangencia_contrato}")
    p.save()
    buffer.seek(0)
    return send_file(buffer, as_attachment=True, download_name=f"contrato_{contrato.id}.pdf",
                     mimetype='application/pdf')

@app.route('/search', methods=['POST'])
def search():
    search_term = request.form['search_term']
    contratos = ContratCond.query.filter(
        (ContratCond.nome.like(f'%{search_term}%')) |
        (ContratCond.cnpj.like(f'%{search_term}%')) |
        (ContratCond.telefone.like(f'%{search_term}%')) |
        (ContratCond.abrangencia_contrato.like(f'%{search_term}%'))
    ).all()
    return render_template('index.html', contratos=contratos)

with app.app_context():
    db.create_all()

if __name__ == '__main__':
    app.run(debug=True)