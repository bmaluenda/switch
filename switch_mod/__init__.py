# Copyright 2015-2017 The Switch Authors. All rights reserved.
# Licensed under the Apache License, Version 2, which is in the LICENSE file.

"""

This package defines the Switch model for Pyomo.

The core modules in this package are timescales, financials, load_zones,
fuels, gen_tech, investment and operations.

An additional module is required to describe fuel costs - either
fuel_cost which specifies a simple flat fuel cost that can vary by load
zone and period, or fuel_markets which specifies a tiered supply curve.

Also, an additional module is required to constrain project dispatch -
either operations.no_commit or operations.unitcommit.

Most applications of Switch will also benefit from optional modules such as 
transmission, local_td, reserves, etc.

This package can be treated as a module that includes all of the mentioned 
core modules instead of having to refer to them individually. This means that
the module list can be specified, for example, as:

switch_modules = ('switch_mod', 'operations.no_commit', 'fuel_markets')

or as

switch_modules = (
    'timescales', 'financials', 'load_zones', 'fuels', 'gen_tech',
    'investment', 'operations', 'operations.no_commit', 'fuel_markets')

You will get an error if you include both the package and the core modules,
because they are redundant.

"""

core_modules = [
    'switch_mod.timescales',
    'switch_mod.financials',
    'switch_mod.load_zones',
    'switch_mod.fuels',
    'switch_mod.gen_tech',
    'switch_mod.investment',
    'switch_mod.operations',
    'switch_mod.export']
