from typing import Dict, List, Tuple
import itertools
import numpy as np

import Bio.PDB

from common.providers import s3Provider, awsKeyProvider
from common.helpers import update_block, fetch_core, load_cif
import logging



peptide_contact_positions = [5,7,9,24,25,33,34,45,59,62,63,64,65,66,67,68,69,70,72,73,74,75,76,77,78,80,81,84,95,97,99,114,116,123,124,133,139,140,142,143,144,146,147,152,155,156,157,158,159,160,163,164,167,168,171]


def build_residue_dictionary(residue):
    coords = [str(coord) for coord in residue["CA"].get_coord()]
    return {
        'residue_id':residue.get_id()[1],
        'chain': residue.parent.get_id(),
        'residue_name':residue.resname,
        'coords': coords,
        'typed_coords':residue["CA"].get_coord()
    }



def build_c_alpha_set(structure, class_i_alpha_chain, peptide_chain):
    c_alpha_set = {
        'peptide':{}
    }
    selected_residues = {
        'class_i_alpha':[],
        'peptide':[]
    }
    for chains in structure:
        for chain in chains:
            if chain.get_id() == class_i_alpha_chain:
                selected_residues['class_i_alpha'] = [residue for residue in chain if residue.get_id()[1] in peptide_contact_positions and residue.get_id()[0] == " "]
            elif chain.get_id() == peptide_chain:
                selected_residues['peptide'] = [residue for residue in chain if residue.get_id()[0] == " "]
    all_residues = selected_residues['peptide'] + selected_residues['class_i_alpha']

    for each in itertools.combinations(all_residues, 2):
        if each[0].parent.get_id() != each[1].parent.get_id():
            pair = {}
            pair['from'] = build_residue_dictionary(each[0])
            pair['to'] = build_residue_dictionary(each[1])
            pair['distance'] = float(np.linalg.norm(pair['from']['typed_coords'] - pair['to']['typed_coords']))
        
            del pair['from']['typed_coords']
            del pair['to']['typed_coords']

            res_id = pair['from']['residue_id']
            if pair['from']['chain'] == peptide_chain:
                if res_id not in c_alpha_set['peptide']:
                    c_alpha_set['peptide'][res_id] = {
                        'best_pair':{},
                        'best_distance':0,
                    'pairs':[]
                }
            c_alpha_set['peptide'][res_id]['pairs'].append(pair)
            if c_alpha_set['peptide'][res_id]['best_distance'] == 0:
                c_alpha_set['peptide'][res_id]['best_pair'] = pair
                c_alpha_set['peptide'][res_id]['best_distance'] = pair['distance']
            elif pair['distance'] < c_alpha_set['peptide'][res_id]['best_distance']:
                c_alpha_set['peptide'][res_id]['best_pair'] = pair
                c_alpha_set['peptide'][res_id]['best_distance'] = pair['distance']
    return c_alpha_set


def measure_distances(pdb_code:str, aws_config:Dict, force:bool=False) -> Dict:
    step_errors = []
    core, success, errors = fetch_core(pdb_code, aws_config)
    s3 = s3Provider(aws_config)
    aligned_key = awsKeyProvider().block_key(pdb_code, 'aligned', 'info')
    aligned, success, errors = s3.get(aligned_key)
    chains_key = awsKeyProvider().block_key(pdb_code, 'chains', 'info')
    chains, success, errors = s3.get(chains_key)
    chain_ids = {'class_i_alpha':[],'peptide':[]}
    for chain in chains:
        if chains[chain]['best_match'] in ['class_i_alpha','peptide']:
            chain_ids[chains[chain]['best_match']] = chains[chain]['chains']
    i = 0
    action = {'c_alpha_distances':{}}
    for assembly_id in aligned['aligned']['files']:
        action['c_alpha_distances'][assembly_id] = {}
        assembly_identifier = f'{pdb_code}_{assembly_id}'
        cif_key = aligned['aligned']['files'][assembly_id]['files']['file_key']
        structure = load_cif(cif_key, assembly_identifier, aws_config)
        c_alpha_set = build_c_alpha_set(structure, chain_ids['class_i_alpha'][i], chain_ids['peptide'][i])
        action['c_alpha_distances'][assembly_id] = c_alpha_set
        i += 1
    c_alpha_distances_key = awsKeyProvider().block_key(pdb_code, 'c_alpha_distances', 'info')
    data, success, errors = s3.put(c_alpha_distances_key, action, data_format='json')
    output = {
        'action':action,
        'core':core
    }
    return output, success, step_errors