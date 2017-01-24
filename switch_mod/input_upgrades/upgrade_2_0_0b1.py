"""
Upgrade input directories from 2.0.0b0 to 2.0.0b1.
Major changes are:
* gen_tech files are merged into project_ files
* The software version number is stored in an input file
* modules.txt explicitly lists each module by its full name
* lz_economic_multiplier is dropped from load_zones
* proj_existing_builds is renamed to proj_existing_and_planned_builds

API Synopsis:
    import switch_mod.input_upgrades.upgrade_2_0_0b1 as b1_upgrade
    if b1_upgrade.can_upgrade_inputs_dir(inputs_dir):
    	b1_upgrade.upgrade_input_dir(inputs_dir):

Command-line Synopsis:
    python -m switch_mod.input_upgrades.upgrade_2_0_0b1 --inputs-dir inputs

"""

import os
import shutil
import pandas
import argparse


upgrades_from = '2.0.0b0'
upgrades_to = '2.0.0b1'

rename_modules = {
    'project.no_commit': 'operations.no_commit',
    'project.unitcommit': 'operations.unitcommit',
    'trans_build': 'investment.trans_build',
    'trans_dispatch': 'operations.trans_dispatch',
    'project.discrete_build': 'investment.proj_discrete_build',
    'project.unitcommit.discrete': 'operations.unitcommit.discrete'
}
module_prefix = 'switch_mod.'
expand_modules = {
    'switch_mod.operations.unitcommit': [
        'switch_mod.operations.unitcommit.commit',
        'switch_mod.operations.unitcommit.fuel_use'
    ],
    'switch_mod.project': [
        'switch_mod.investment.proj_build',
        'switch_mod.operations.proj_dispatch'
    ]
}
core_modules = [
    'switch_mod.timescales',
    'switch_mod.financials',
    'switch_mod.load_zones',
    'switch_mod.fuels',
    'switch_mod.investment.proj_build',
    'switch_mod.operations.proj_dispatch',
    'switch_mod.export'
]
version_file = 'switch_inputs_version.txt'

def can_upgrade_inputs_dir(inputs_dir):
    """
    Determine if input directory can be upgraded with this script.
    Returns True/False
    """
    # Test if the input directory needs to be upgraded based on the 
    # absense of switch_version.txt and the presense of generator_info.tab
    version = None
    version_path = os.path.join(inputs_dir, version_file)
    if os.path.isfile(version_path):
        with open(version_path, 'r') as f:
            version = f.readline().strip()
    elif os.path.isfile(os.path.join(inputs_dir, 'generator_info.tab')):
        version = upgrades_from
    if version is None or version != upgrades_from:
        return False
    return True

def upgrade_input_dir(inputs_dir):
    """
    Upgrade an input directory. If the directory has already 
    been upgraded, this will have no effect.
    """
    if not can_upgrade_inputs_dir(inputs_dir):
        print "Skipping upgrade for inputs directory {}.".format(inputs_dir)
        return False

    # Make a backup of the inputs_dir, unless that already exists
    inputs_backup = os.path.join(inputs_dir, 'inputs_v'+upgrades_from)
    #shutil.make_archive(inputs_backup, 'zip', inputs_dir)
    if not os.path.isdir(inputs_backup):
        shutil.copytree(inputs_dir, inputs_backup)

    # Write a new version text file.
    version_path = os.path.join(inputs_dir, version_file)
    with open(version_path, 'w') as f:
        f.write(upgrades_to + "\n")

    # Does 'modules' need to get renamed to 'modules.txt'?
    modules_path_old = os.path.join(inputs_dir, 'modules')
    modules_path = os.path.join(inputs_dir, 'modules.txt')
    if os.path.isfile(modules_path_old):
        shutil.move(modules_path_old, modules_path)

    # Upgrade module listings
    with open(modules_path, 'rb') as f:
        module_list = [line for line in f.read().split('\n') if line and line[0] != '#']
    module_list_orig = [m for m in module_list]
    new_module_list=[]
    for i, module in enumerate(module_list):
        # Rename modules
        if module in rename_modules:
            module_list[i] = rename_modules[module]
#         # Add prefixes
#         if module_prefix not in module:
#             module_list[i] = module_prefix + module
#         # Copy module to new list or expand package listing
#         if module not in expand_modules:
#             new_module_list.append(module_list[i])
#         else:
#             new_module_list += expand_modules[module]
#     # Stuff core modules into the beginning as needed
#     if new_module_list[0] != core_modules[0]:
#         new_module_list = ['# Core Modules'] + core_modules + \
#                           ['# Custom Modules'] + new_module_list
#     import pdb; pdb.set_trace()
    # Write a new modules.txt file
    with open(modules_path, 'w') as f:
#        for module in new_module_list:
        for module in module_list:
            f.write(module + "\n")

    # Merge generator_info with project_info
    gen_info_path = os.path.join(inputs_dir, 'generator_info.tab')
    gen_info_df = pandas.read_csv(gen_info_path, na_values=['.'], sep='\t')
    gen_info_col_renames = {
        'generation_technology': 'proj_gen_tech',
        'g_energy_source': 'proj_energy_source',
        'g_max_age': 'proj_max_age',
        'g_scheduled_outage_rate': 'proj_scheduled_outage_rate.default',
        'g_forced_outage_rate': 'proj_forced_outage_rate.default',
        'g_variable_o_m': 'proj_variable_om.default',
        'g_full_load_heat_rate': 'proj_full_load_heat_rate.default',
        'g_is_variable': 'proj_is_variable',
        'g_is_baseload': 'proj_is_baseload',
        'g_min_build_capacity': 'proj_min_build_capacity',
        'g_is_cogen': 'proj_is_cogen',
        'g_storage_efficiency': 'proj_storage_efficiency.default',
        'g_store_to_release_ratio': 'proj_store_to_release_ratio.default'
    }
    drop_cols = [c for c in gen_info_df if c not in gen_info_col_renames]
    for c in drop_cols:
        del gen_info_df[c]
    gen_info_df.rename(columns=gen_info_col_renames, inplace=True)
    proj_info_path = os.path.join(inputs_dir, 'project_info.tab')
    proj_info_df = pandas.read_csv(proj_info_path, na_values=['.'], sep='\t')
    proj_info_df = pandas.merge(proj_info_df, gen_info_df, on='proj_gen_tech', how='left')

    # An internal function to apply a column of default values to the actual column
    def update_cols_with_defaults(df, col_list):
        for col in col_list:
            default_col = col + '.default'
            if default_col not in df:
                continue
            if col not in df:
                df.rename(columns={default_col: col}, inplace=True)
            else:
                df[col].fillna(df[default_col], inplace=True)
                del df[default_col]

    columns_with_defaults = ['proj_scheduled_outage_rate', 'proj_forced_outage_rate',
                             'proj_variable_om', 'proj_full_load_heat_rate',
                             'proj_storage_efficiency', 'proj_store_to_release_ratio']
    update_cols_with_defaults(proj_info_df, columns_with_defaults)
    proj_info_df.to_csv(proj_info_path, sep='\t', na_rep='.', index=False)
    os.remove(gen_info_path)

    ###
    # Get load zone economic multipliers (if available), then drop them.
    load_zone_path = os.path.join(inputs_dir, 'load_zones.tab')
    load_zone_df = pandas.read_csv(load_zone_path, na_values=['.'], sep='\t')
    if 'lz_cost_multipliers' in load_zone_df:
        load_zone_df['lz_cost_multipliers'].fillna(1)
    else:
        load_zone_df['lz_cost_multipliers'] = 1
    load_zone_keep_cols = [c for c in load_zone_df if c != 'lz_cost_multipliers']
    load_zone_df.to_csv(load_zone_path, sep='\t', na_rep='.', 
                        index=False, columns=load_zone_keep_cols)

    ###
    # Merge gen_new_build_costs into proj_build_costs

    # Translate default generator costs into costs for each project
    gen_build_path = os.path.join(inputs_dir, 'gen_new_build_costs.tab')
    if os.path.isfile(gen_build_path):
        gen_build_df = pandas.read_csv(gen_build_path, na_values=['.'], sep='\t')
        new_col_names = {
            'generation_technology': 'proj_gen_tech',
            'investment_period': 'build_year',
            'g_overnight_cost': 'proj_overnight_cost.default',
            'g_storage_energy_overnight_cost': 'proj_storage_energy_overnight_cost.default',
            'g_fixed_o_m': 'proj_fixed_om.default'}
        gen_build_df.rename(columns=new_col_names, inplace=True)
        new_proj_builds = pandas.merge(
            gen_build_df, proj_info_df[['PROJECT', 'proj_gen_tech', 'proj_load_zone']],
            on='proj_gen_tech')
        # Factor in the load zone cost multipliers
        new_proj_builds = pandas.merge(
            load_zone_df[['LOAD_ZONE', 'lz_cost_multipliers']], new_proj_builds,
            left_on='LOAD_ZONE', right_on='proj_load_zone', how='right')
        new_proj_builds['proj_overnight_cost.default'] *= new_proj_builds['lz_cost_multipliers']
        new_proj_builds['proj_fixed_om.default'] *= new_proj_builds['lz_cost_multipliers']
        # Clean up
        for drop_col in ['LOAD_ZONE', 'proj_gen_tech', 'proj_load_zone', 'lz_cost_multipliers']:
            del new_proj_builds[drop_col]

        # Merge the expanded gen_new_build_costs data into proj_build_costs
        project_build_path = os.path.join(inputs_dir, 'proj_build_costs.tab')
        if os.path.isfile(project_build_path):
            project_build_df = pandas.read_csv(project_build_path, na_values=['.'], sep='\t')
            project_build_df = pandas.merge(project_build_df, new_proj_builds,
                                             on=['PROJECT', 'build_year'], how='outer')
        else:
            # Make sure the order of the columns is ok since merge won't ensuring that.
            idx_cols = ['PROJECT', 'build_year']
            dat_cols = [c for c in new_proj_builds if c not in idx_cols]
            col_order = idx_cols + dat_cols
            project_build_df = new_proj_builds[col_order]
        columns_with_defaults = ['proj_overnight_cost', 'proj_fixed_om', 
                                 'proj_storage_energy_overnight_cost']
        update_cols_with_defaults(project_build_df, columns_with_defaults)
        project_build_df.to_csv(project_build_path, sep='\t', na_rep='.', index=False)
        os.remove(gen_build_path)
    
    # Rename proj_existing_builds.tab to proj_existing_planned_builds.tab
    proj_constrained_path_old = os.path.join(inputs_dir, 'proj_existing_builds.tab')
    proj_constrained_path = os.path.join(inputs_dir, 'proj_build_constraints.tab')
    if os.path.isfile(proj_constrained_path_old):
        shutil.move(proj_constrained_path_old, proj_constrained_path)
    
    # Rename the proj_existing_cap column to proj_predetermined_cap
    if os.path.isfile(proj_constrained_path):
        project_cons_df = pandas.read_csv(proj_constrained_path, na_values=['.'], sep='\t')
        project_cons_df.rename(columns={'proj_existing_cap': 'proj_predetermined_cap'},
                               inplace=True)
        project_cons_df.to_csv(proj_constrained_path, sep='\t', na_rep='.', index=False)
#    import pdb; pdb.set_trace()


def main(inputs_dir):
    if not os.path.isdir(inputs_dir):
        print "Error: Input directory {} does not exist.".format(inputs_dir)
        return -1    
    upgrade_input_dir(inputs_dir)

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument("--inputs-dir", default="inputs", 
        help='Directory containing input files (default is "inputs")')
    args = parser.parse_args()
    main(inputs_dir=args.inputs_dir)
