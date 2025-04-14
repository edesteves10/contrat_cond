import os
import datetime
import sqlite3
from flask import Flask, render_template, request, redirect, url_for, send_file, flash
from flask_sqlalchemy import SQLAlchemy
from reportlab.pdfgen import canvas
from io import BytesIO
import re
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash

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
    username = db.Column(db.String(100), unique=True)
    password_hash = db.Column(db.String(200))

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class ContratCond(db.Model):
    # ... (seu código existente)
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

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username).first()
        if user and user.check_password(password):
            login_user(user)
            return redirect(url_for('index'))
        else:
            flash('Usuário ou senha incorretos.', 'error')
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
        nome = request.form['nome']
        cnpj = request.form['cnpj']
        endereco = request.form['endereco']
        cep = request.form['cep']
        estado = request.form['estado']
        telefone = request.form['telefone']
        email = request.form['email']
        valor_contrato = request.form['valor_contrato']
        inicio_contrato = request.form['inicio_contrato']
        termino_contrato = request.form['termino_contrato']
        abrangencia_contrato = request.form['abrangencia_contrato']

        novo_contrato = ContratCond(nome=nome, cnpj=cnpj, endereco=endereco, cep=cep, estado=estado, telefone=telefone, email=email, valor_contrato=valor_contrato, inicio_contrato=inicio_contrato, termino_contrato=termino_contrato, abrangencia_contrato=abrangencia_contrato)
        db.session.add(novo_contrato)
        db.session.commit()
        return redirect(url_for('index'))

    page = request.args.get('page', 1, type=int)
    contratos = ContratCond.query.paginate(page=page, per_page=10)
    return render_template('index.html', contratos=contratos)

@app.route('/edit/<int:id>', methods=['GET', 'POST'])
@login_required
def edit(id):
    contrato = ContratCond.query.get_or_404(id)
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
        contrato.termino_contrato = request.form['termino_contrato']
        contrato.abrangencia_contrato = request.form['abrangencia_contrato']
        db.session.commit()
        return redirect(url_for('index'))
    return render_template('edit.html', contrato=contrato)

@app.route('/pdf/<int:id>')
@login_required
def generate_pdf(id):
    contrato = ContratCond.query.get_or_404(id)
    output = BytesIO()
    p = canvas.Canvas(output)
    p.drawString(100, 800, f"Nome: {contrato.nome}")
    p.drawString(100, 780, f"CNPJ: {contrato.cnpj}")
    p.drawString(100, 760, f"Endereço: {contrato.endereco}")
    p.drawString(100, 740, f"CEP: {contrato.cep}")
    p.drawString(100, 720, f"Estado: {contrato.estado}")
    p.drawString(100, 700, f"Telefone: {contrato.telefone}")
    p.drawString(100, 680, f"Email: {contrato.email}")
    p.drawString(100, 660, f"Valor do Contrato: {contrato.valor_contrato}")
    p.drawString(100, 640, f"Início do Contrato: {contrato.inicio_contrato}")
    p.drawString(100, 620, f"Término do Contrato: {contrato.termino_contrato}")
    p.drawString(100, 600, f"Abrangência do Contrato: {contrato.abrangencia_contrato}")
    p.save()
    output.seek(0)
    return send_file(output, as_attachment=True, download_name=f"contrato_{contrato.id}.pdf", mimetype='application/pdf')

@app.route('/search', methods=['POST'])
@login_required
def search():
    query = request.form['query']
    contratos = ContratCond.query.filter(ContratCond.nome.ilike(f'%{query}%')).all()
    return render_template('index.html', contratos=contratos)
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        hashed_password = generate_password_hash(password)
        new_user = User(username=username, password_hash=hashed_password)
        db.session.add(new_user)
        db.session.commit()
        return redirect(url_for('login'))
    return render_template('register.html')

with app.app_context():
    db.create_all()

if __name__ == '__main__':
    app.run(debug=True)