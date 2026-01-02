import json
import sqlite3

import pytest
import app as app_module


def test_init_db_and_load_upgrades():
    # Call init_db (should call patched run_migrations which is a noop)
    app_module.init_db()

    upgrades = app_module.load_upgrades()
    assert isinstance(upgrades, list)
    assert len(upgrades) > 0

    # Check first upgrade fields
    first = upgrades[0]
    assert 'name' in first and 'price' in first and 'cps' in first and 'level' in first
    assert first['level'] == 0  # seeded upgrades should start with level 0


def test_purchase_and_decrease_endpoint(client=None):
    # Use Flask test client
    client = app_module.app.test_client()

    upgrades = app_module.load_upgrades()
    name = upgrades[0]['name']

    # Purchase once
    resp = client.post(f'/api/upgrade/{name}')
    assert resp.status_code == 200
    data = resp.get_json()
    assert data.get('success') is True
    assert data.get('upgrade') and data['upgrade']['level'] == 1

    # Purchase again
    resp = client.post(f'/api/upgrade/{name}')
    assert resp.status_code == 200
    data = resp.get_json()
    assert data.get('upgrade')['level'] == 2

    # Decrease
    resp = client.post(f'/api/upgrade/{name}/decrease')
    assert resp.status_code == 200
    data = resp.get_json()
    assert data.get('success') is True
    assert data['upgrade']['level'] == 1


def test_reset_endpoint_creates_backup_and_resets():
    client = app_module.app.test_client()

    # Ensure an upgrade has been purchased
    upgrades = app_module.load_upgrades()
    name = upgrades[0]['name']
    client.post(f'/api/upgrade/{name}')

    # Reset
    resp = client.post('/api/reset')
    assert resp.status_code == 200
    data = resp.get_json()
    assert data.get('success') is True
    assert 'backup' in data

    # Verify levels are zero
    upgrades_after = app_module.load_upgrades()
    for u in upgrades_after:
        assert u['level'] == 0


def test_get_upgrades_endpoint():
    client = app_module.app.test_client()
    resp = client.get('/api/upgrades')
    assert resp.status_code == 200
    data = resp.get_json()
    assert 'upgrades' in data and isinstance(data['upgrades'], list)
    assert 'total_cps' in data

