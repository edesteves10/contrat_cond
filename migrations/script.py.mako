import logging
from logging.config import fileConfig
import os 
from alembic import context
from sqlalchemy import engine_from_config, pool

# --- CONFIGURAÇÃO DA SUA APLICAÇÃO FLASK ---
from flask import current_app
# Importe o objeto 'db' (SQLAlchemy) do seu módulo principal
# Certifique-se de que 'contrat_cond' é o nome do seu pacote Flask
# Se você usa Flask-SQLAlchemy, o 'db' deve ser importado
from contrat_cond import db 
target_metadata = db.metadata

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# CORREÇÃO CRÍTICA PARA HEROKU: 
# Ajusta o caminho do alembic.ini para que ele possa ser encontrado 
# na raiz do projeto (subindo um nível: '..').
config_dir = os.path.dirname(__file__)
config_path = os.path.join(config_dir, '..', config.config_file_name)
fileConfig(config_path) # Agora usa o caminho correto e completo

# Definição do logger (necessário após fileConfig)
logger = logging.getLogger('alembic.env')


def run_migrations_online():
    """Executa as migrações no modo 'online' (conectado ao DB)."""
    
    # Esta é a lógica que Flask-Migrate usa para descobrir a URL correta no contexto do Heroku
    if current_app:
        # Puxa a URL do banco de dados da configuração do Flask
        url = current_app.config.get('SQLALCHEMY_DATABASE_URI')
        
        # Tenta usar a variável de ambiente (Heroku) se não estiver configurada
        if not url:
            url = os.environ.get('DATABASE_URL')
            
        # Se ainda assim for None, usa o valor padrão do alembic.ini (fallback)
        if not url:
            url = context.config.get_main_option("sqlalchemy.url")

        # Atualiza a configuração do Alembic com a URL do banco de dados
        context.config.set_main_option('sqlalchemy.url', url)
        
        # Passa a configuração de SQLAlchemy
        connectable = engine_from_config(
            context.config.get_section(context.config.config_ini_section, {}), # Adicionado {} para segurança
            prefix='sqlalchemy.',
            poolclass=pool.NullPool,
        )

        with connectable.connect() as connection:
            context.configure(
                connection=connection,
                target_metadata=target_metadata,
                render_as_batch=True # Recomendado para SQLite e alguns comandos
            )

            with context.begin_transaction():
                context.run_migrations()

def run_migrations_offline():
    """Executa as migrações no modo 'offline'."""
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

# Inicia as migrações dependendo se o app Flask está carregado
if context.is_offline_mode():
    run_migrations_offline()
else:
    # Verifica se o aplicativo Flask está disponível e configura o modo de execução.
    if current_app:
        run_migrations_online()
    else:
        # Se o comando foi rodado sem o contexto Flask (raro no Heroku, mas seguro)
        run_migrations_offline()