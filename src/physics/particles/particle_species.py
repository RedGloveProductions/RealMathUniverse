"""
Particle species table.

Real values should be stored as reference values. Simulation values should be
derived through documented mappings.
"""

from __future__ import annotations


PARTICLE_SPECIES = {
    "electron": {
        "group": "lepton",
        "charge_e": -1.0,
        "real_mass_kg": 9.1093837015e-31,
        "simulation_mass": 1.0,
    },
    "positron": {
        "group": "lepton",
        "charge_e": 1.0,
        "real_mass_kg": 9.1093837015e-31,
        "simulation_mass": 1.0,
    },
    "photon_like": {
        "group": "boson_like_excitation",
        "charge_e": 0.0,
        "real_mass_kg": 0.0,
        "simulation_mass": 0.0,
    },
}
