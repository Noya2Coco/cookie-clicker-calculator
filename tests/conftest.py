import os
import sqlite3
import pytest

# Ensure `seeds` module is importable when running tests from different CWDs
try:
    import seeds
except ModuleNotFoundError:
    import importlib.util, sys
    project_root = os.path.dirname(os.path.dirname(__file__))
    seeds_path = os.path.join(project_root, 'seeds.py')
    if os.path.exists(seeds_path):
        spec = importlib.util.spec_from_file_location('seeds', seeds_path)
        seeds = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(seeds)
        sys.modules['seeds'] = seeds
    else:
        raise

import sys
# Ensure project root is on sys.path so `import app` works under pytest
project_root = os.path.dirname(os.path.dirname(__file__))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

import app as app_module


@pytest.fixture
def temp_db_path(tmp_path):
    db_file = tmp_path / "data.db"
    return str(db_file)


def _create_schema_and_seed(db_path):
    conn = sqlite3.connect(db_path, check_same_thread=False)
    cur = conn.cursor()
    cur.execute('''
        CREATE TABLE IF NOT EXISTS upgrades (
            name TEXT PRIMARY KEY,
            price REAL NOT NULL,
            level INTEGER NOT NULL DEFAULT 0,
            cps REAL NOT NULL DEFAULT 0,
            position INTEGER NOT NULL DEFAULT 0
        )
    ''')
    cur.execute('''
        CREATE TABLE IF NOT EXISTS defaults (
            name TEXT PRIMARY KEY,
            price REAL NOT NULL,
            cps REAL NOT NULL,
            seed_level INTEGER NOT NULL DEFAULT 0
        )
    ''')
    conn.commit()

    # Insert seeds
    for pos, item in enumerate(seeds.SEEDS):
        cur.execute('INSERT OR REPLACE INTO defaults (name, price, cps, seed_level) VALUES (?,?,?,?)',
                    (item['name'], float(item['price']), float(item['cps']), int(item.get('seed_level', 0))))
        cur.execute('INSERT OR REPLACE INTO upgrades (name, price, level, cps, position) VALUES (?,?,?,?,?)',
                    (item['name'], float(item['price']), 0, float(item['cps']), pos))
    conn.commit()
    conn.close()


@pytest.fixture(autouse=True)
def patch_db(monkeypatch, temp_db_path):
    """Monkeypatch app to use a temporary database and to stub migrations/backup."""

    # Ensure DB exists and seeded
    _create_schema_and_seed(temp_db_path)

    # Patch get_db_connection to return connections to temp db
    def _get_db_connection():
        return sqlite3.connect(temp_db_path, check_same_thread=False)

    monkeypatch.setattr(app_module, 'get_db_connection', _get_db_connection)

    # Patch run_migrations.upgrade_head to a no-op that seeds the temp DB
    try:
        import run_migrations

        def _upgrade_head_noop():
            # Ensure the temp DB is seeded (already done)
            return None

        monkeypatch.setattr(run_migrations, 'upgrade_head', _upgrade_head_noop)
    except Exception:
        pass

    # Patch create_db_backup to avoid filesystem operations
    def _create_db_backup_stub():
        # emulate creation of backup name
        return 'test_backup.db'

    monkeypatch.setattr(app_module, 'create_db_backup', _create_db_backup_stub)

    yield

    # cleanup: nothing specific (tmp_path is auto-cleaned)
