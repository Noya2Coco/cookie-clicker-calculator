# Default upgrades defined in code (name, price, cps)
# `seed_level` here is only used to populate the `defaults` table.
# Application `upgrades` rows are initialized with level=0 by migrations.
# Per request: all default seed levels should be 0 except AutoClick which should be 1.
SEEDS = [
    {"name": "AutoClick", "price": 30, "cps": 0.1, "seed_level": 1},
    {"name": "GrandMa", "price": 100, "cps": 0.3, "seed_level": 0},
    {"name": "C-Robot", "price": 1000, "cps": 1, "seed_level": 0},
    {"name": "CookieFarm", "price": 10000, "cps": 3.1, "seed_level": 0},
    {"name": "C-Factory", "price": 50000, "cps": 6, "seed_level": 0},
    {"name": "S-Factory", "price": 200000, "cps": 20, "seed_level": 0},
    {"name": "X-Factory", "price": 500000, "cps": 40, "seed_level": 0},
    {"name": "CookieCloner", "price": 1000000, "cps": 70, "seed_level": 0},
    {"name": "C-Cern", "price": 5000000, "cps": 300, "seed_level": 0},
    {"name": "Atomic-C", "price": 30000000, "cps": 1500, "seed_level": 0},
    {"name": "Alien Robot", "price": 70000000, "cps": 3000, "seed_level": 0},
    {"name": "Alien Lab", "price": 200000000, "cps": 8000, "seed_level": 0},
    {"name": "Alien Lab v2", "price": 400000000, "cps": 15000, "seed_level": 0},
    {"name": "Alien Tech", "price": 600000000, "cps": 20000, "seed_level": 0},
    {"name": "Alien C-X", "price": 1000000000, "cps": 30000, "seed_level": 0},
    {"name": "Nano Cookie", "price": 3000000000, "cps": 80000, "seed_level": 0},
    {"name": "Molecular-C", "price": 5000000000, "cps": 120000, "seed_level": 0},
    {"name": "Virus Cookie", "price": 10000000000, "cps": 200000, "seed_level": 0},
    {"name": "Proto Cookie", "price": 20000000000, "cps": 350000, "seed_level": 0},
    {"name": "Synaptic-C", "price": 50000000000, "cps": 600000, "seed_level": 0},
    {"name": "Hydrogenic-C", "price": 100000000000, "cps": 1000000, "seed_level": 0},
    {"name": "Uranium-C", "price": 200000000000, "cps": 1500000, "seed_level": 0},
    {"name": "Plutonium-C", "price": 400000000000, "cps": 2500000, "seed_level": 0},
    {"name": "Krypto-C", "price": 800000000000, "cps": 4000000, "seed_level": 0},
    {"name": "RedKrypto-C", "price": 1600000000000, "cps": 7000000, "seed_level": 0},
    {"name": "Moon-C", "price": 2500000000000, "cps": 10000000, "seed_level": 0},
    {"name": "Galaxy-C", "price": 4000000000000, "cps": 15000000, "seed_level": 0},
    {"name": "Galaxy-X", "price": 8000000000000, "cps": 25000000, "seed_level": 0},
    {"name": "Cookie Hack", "price": 15000000000000, "cps": 40000000, "seed_level": 0},
    {"name": "Cookie God", "price": 1000000000000000, "cps": 1000000000, "seed_level": 0}
]
