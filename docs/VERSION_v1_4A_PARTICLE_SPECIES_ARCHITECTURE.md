# RealMathUniverse v1.4A Particle Species Architecture

Major patch after v1.3F9H stable.

Adds config-driven species metadata and the first deterministic GPU species pass.

Species included:
0 crab_default, 1 electron, 2 positron, 3 electron_neutrino, 4 up_quark, 5 down_quark,
6 photon_like, 7 gluon_like, 8 higgs_excitation, 9 proton_like, 10 neutron_like,
11 muon, 12 tau, 13 muon_neutrino, 14 tau_neutrino, 15 strange_quark, 16 charm_quark,
17 top_quark, 18 bottom_quark, 19 W_like, 20 Z_like, 21 meson_like.

This is a reduced simulation architecture layer, not full particle physics.
VCV /ch/9-/ch/12 now modulate species differently in the GPU force model.
