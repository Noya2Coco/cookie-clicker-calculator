"""Create upgrades and defaults tables and seed default data
Revision ID: 0001_create_defaults_and_upgrades
Revises: 
Create Date: 2026-01-02
"""
from alembic import op
import sqlalchemy as sa
import os
import json

# revision identifiers, used by Alembic.
revision = '0001_create_defaults_and_upgrades'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # Create upgrades table
    op.create_table(
        'upgrades',
        sa.Column('name', sa.Text(), primary_key=True),
        sa.Column('price', sa.Float(), nullable=False),
        sa.Column('level', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('cps', sa.Float(), nullable=False, server_default='0'),
        sa.Column('position', sa.Integer(), nullable=False, server_default='0')
    )

    # Create defaults table to store seed data
    op.create_table(
        'defaults',
        sa.Column('name', sa.Text(), primary_key=True),
        sa.Column('price', sa.Float(), nullable=False),
        sa.Column('cps', sa.Float(), nullable=False),
        sa.Column('seed_level', sa.Integer(), nullable=False, server_default='0')
    )

    # Insert seed data. Prefer importing `seeds.SEEDS` (hard-coded),
    # fallback to reading `cookie_clicker_upgrades.json` if seeds module is not available.
    bind = op.get_bind()
    data = None
    try:
        # Try to import the seeds module from project root
        import importlib.util
        spec = importlib.util.find_spec('seeds')
        if spec is not None:
            seeds = importlib.import_module('seeds')
            data = getattr(seeds, 'SEEDS', None)
    except Exception:
        data = None

    if not data:
        base = os.path.dirname(os.path.dirname(__file__))
        json_path = os.path.join(base, 'cookie_clicker_upgrades.json')
        if os.path.exists(json_path):
            with open(json_path, 'r', encoding='utf-8') as f:
                try:
                    data = json.load(f)
                except Exception:
                    data = []
        else:
            data = []

    for pos, item in enumerate(data):
        name = item.get('name')
        price = float(item.get('price', 0))
        cps = float(item.get('cps', 0))
        seed_level = int(item.get('seed_level', item.get('level', 0)))
        # Insert into defaults
        bind.execute(sa.text(
            "INSERT OR REPLACE INTO defaults (name, price, cps, seed_level) VALUES (:name, :price, :cps, :seed_level)"
        ), {"name": name, "price": price, "cps": cps, "seed_level": seed_level})
        # Insert into upgrades with level = 0 (fresh start)
        bind.execute(sa.text(
            "INSERT OR REPLACE INTO upgrades (name, price, level, cps, position) VALUES (:name, :price, :level, :cps, :position)"
        ), {"name": name, "price": price, "level": 0, "cps": cps, "position": pos})


def downgrade():
    op.drop_table('defaults')
    op.drop_table('upgrades')
