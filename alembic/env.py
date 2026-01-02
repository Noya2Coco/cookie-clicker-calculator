from __future__ import with_statement
import os
from logging.config import fileConfig
from alembic import context
from sqlalchemy import create_engine, pool

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# set the SQLAlchemy URL dynamically if not provided
base_dir = os.path.dirname(os.path.dirname(__file__))
if not config.get_main_option('sqlalchemy.url'):
    db_path = os.path.join(base_dir, 'data.db')
    config.set_main_option('sqlalchemy.url', f"sqlite:///{db_path.replace('\\\\', '/')}")

# No metadata object to autogenerate against
target_metadata = None


def run_migrations_offline():
    url = config.get_main_option('sqlalchemy.url')
    context.configure(url=url, literal_binds=True)

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online():
    connectable = create_engine(config.get_main_option('sqlalchemy.url'), poolclass=pool.NullPool)

    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
