"""
Utility to run Alembic migrations programmatically.
"""
import os
from alembic.config import Config
from alembic import command


def upgrade_head():
    base = os.path.dirname(__file__)
    alembic_cfg_path = os.path.join(base, 'alembic.ini')
    cfg = Config(alembic_cfg_path)
    # Make sure script location is resolved relative to project
    cfg.set_main_option('script_location', os.path.join(base, 'alembic'))
    # Ensure SQLAlchemy URL points to local data.db
    db_url = f"sqlite:///{os.path.join(base, 'data.db').replace('\\', '/') }"
    cfg.set_main_option('sqlalchemy.url', db_url)
    command.upgrade(cfg, 'head')


if __name__ == '__main__':
    upgrade_head()
