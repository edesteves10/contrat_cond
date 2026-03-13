from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_migrate import Migrate
# Inicializa as extensões sem associá-las a um app (ainda)
db = SQLAlchemy()
login_manager = LoginManager()
migrate = Migrate() # 🌟 Inicialização do objeto Migrate adicionada 🌟

# Define a view de login (a rota que o Flask-Login deve redirecionar)
login_manager.login_view = 'login'

# Define a mensagem que o usuário verá ao ser redirecionado
login_manager.login_message = 'Por favor, faça login para acessar esta página.'
login_manager.login_message_category = 'info'
