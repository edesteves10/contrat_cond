# migrations/env.py
import os  # <-- Importação do módulo de sistema operacional
from logging.config import fileConfig
import os # ESSENCIAL: precisamos do 'os'
from alembic import context
from sqlalchemy import engine_from_config, pool

# --- CONFIGURAÇÃO DA SUA APLICAÇÃO FLASK ---
from flask import current_app
# Importe o objeto 'db' (SQLAlchemy) do seu módulo principal
from contrat_cond import db 
target_metadata = db.metadata

config = context.config

# CORREÇÃO CRÍTICA PARA HEROKU (Linhas 14, 15, 16)
# Constrói o caminho completo: /app/migrations/alembic.ini
config_dir = os.path.dirname(__file__)
config_path = os.path.join(config_dir, '..', config.config_file_name)
fileConfig(config_path) # Agora usa o caminho correto e completo

# --- RESTANTE DO CÓDIGO (run_migrations_online/offline) ---

def run_migrations_online():
    """Run migrations in 'online' mode."""
    
    if current_app:
        # Puxa a URL do banco de dados da configuração do Flask
        url = current_app.config.get('SQLALCHEMY_DATABASE_URI')
        
        # Tenta usar a variável de ambiente (Heroku) se não estiver configurada
        if not url:
             url = os.environ.get('DATABASE_URL')
             
        # Se ainda assim for None, usa o valor padrão do alembic.ini
        if not url:
            url = context.config.get_main_option("sqlalchemy.url")

        context.config.set_main_option('sqlalchemy.url', url)
        
        # Passa a configuração de SQLAlchemy
        connectable = engine_from_config(
            context.config.get_section(context.config.config_ini_section),
            prefix='sqlalchemy.',
            poolclass=pool.NullPool,
        )

        with connectable.connect() as connection:
            context.configure(
                connection=connection,
                target_metadata=target_metadata,
                render_as_batch=True
            )

            with context.begin_transaction():
                context.run_migrations()

def run_migrations_offline():
    """Run migrations in 'offline' mode.
    ... [código omitido para brevidade] ...
    """
    url = context.config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        render_as_batch=True
    )

    with context.begin_transaction():
        context.run_migrations()

# Verifica se o aplicativo Flask está disponível e configura o modo de execução.
if current_app:
    run_migrations_online()
else:
    run_migrations_offline()