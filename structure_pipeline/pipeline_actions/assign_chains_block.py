from common.providers import s3Provider, awsKeyProvider, PDBeProvider
from common.helpers import pdb_loader, update_block, three_letter_to_one, fetch_constants

from common.helpers import fetch_constants, fetch_core, update_block

import logging



def assign_chain(chain_length, molecule, molecule_search_terms=None):
    if not molecule_search_terms:
        molecule_search_terms = molecule.replace('-',' ').split(' ')
    
    max_match_count = 0
    best_match = 'unmatched'
    chains = fetch_constants('chains')
    for chain in chains:
        if chain_length < 20:
            best_match = 'peptide'
        else:
            matches = [item for item in molecule_search_terms if item in chains[chain]['features']]
            if chain_length > chains[chain]['length'] + chains[chain]['range'][0] and chain_length < chains[chain]['length'] + chains[chain]['range'][1]:
                in_range = True
            else:
                in_range = False
            match_count = len(matches)
            if in_range:
                match_count += 1
            if match_count > max_match_count and in_range:
                max_match_count = match_count
                best_match = chains[chain]['label']
    return best_match




def assign_chains(pdb_code, aws_config, force=False):
    set_errors = []
    core, success, errors = fetch_core(pdb_code, aws_config)
    action = {}
    update = {'peptide':core['peptide']}
    molecules_info, success, errors = PDBeProvider(pdb_code).fetch_molecules()
    for chain in molecules_info:
        if 'molecule' not in chain:
            if 'length' in chain:
                chain_id = chain['entity_id']
                action[chain_id] = {
                    'molecule':chain['molecule_name'][0].lower(),
                    'chains':chain['in_chains'],
                    'length':chain['length'],
                    'gene_name':chain['gene_name'],
                    'start':[source['mappings'][0]['start']['residue_number'] for source in chain['source']],
                    'end':[source['mappings'][0]['end']['residue_number'] for source in chain['source']]
                }

                chain_length = chain['length']
                molecule_search_terms = chain['molecule_name'][0].lower().split(' ')
                if 'gene_name' in chain:
                    for item in chain['gene_name']:
                        molecule_search_terms.append(item)
                best_match = assign_chain(chain_length, None, molecule_search_terms=molecule_search_terms)
                action[chain_id]['best_match'] = best_match
                action[chain_id]['sequences'] = [chain['sequence']]
                if best_match in ['class_i_alpha', 'class_ii_alpha']:
                    update['organism'] = {
                        'scientific_name': chain['source'][0]['organism_scientific_name']
                    }
                if best_match == 'peptide':
                    update['peptide']['sequence'] = chain['sequence']
    s3 = s3Provider(aws_config)
    chains_key = awsKeyProvider().block_key(pdb_code, 'chains', 'info')
    s3.put(chains_key, action)
    data, success, errors = update_block(pdb_code, 'core', 'info', update, aws_config)
    output = {
        'action':action,
        'core':data
    }
    return output, True, set_errors





def alike_chains(pdb_code, aws_config, force=False):
    core_key = awsKeyProvider().block_key(pdb_code, 'core', 'info')
    step_errors = []
    s3 = s3Provider(aws_config)
    data, success, errors = s3.get(core_key)
    filepath = awsKeyProvider().structure_key(pdb_code, 'raw')
    pdb_data, success, errors = s3.get(filepath, data_format='pdb')
    chain_starts = {}
    chain_lengths = {}
    chain_sequences = {}
    chainset = {}
    if success:
        structure = pdb_loader(pdb_data)
        if structure:
            for chains in structure:
                for chain in chains:
                    residues = [aa for aa in chain.get_residues() if aa.id[0] == " "]
                    chain_sequence = [three_letter_to_one(aa.resname).upper() for aa in residues]
                    chain_starts[chain.id.lower()] = residues[0].id[1]
                    chain_lengths[chain.id.lower()] = len(chain_sequence)
                    chain_sequences[chain.id.lower()] = ''.join(chain_sequence)
    if len(data['components']) == 0:
        step_errors.append('missing_components_dictionary')
    else:
        for component in data['components']:
            this_component = data['components'][component]
            chainset[component] = {}
            chainset[component]['chains'] = this_component['chain']
            chainset[component]['molecule'] = this_component['molecule']
            chain_length = 0
            i = 0
            chainset[component]['sequences'] = []
            chainset[component]['start'] = []
            for chain_id in chainset[component]['chains']:
                chain_length += chain_lengths[chain_id]
                chainset[component]['sequences'].append(chain_sequences[chain_id])
                chainset[component]['start'].append(chain_starts[chain_id])
                i += 1
            chain_length = round(chain_length/i)
            chainset[component]['best_match'] = assign_chain(chain_length,this_component['molecule'])
            if chainset[component]['best_match'] == 'unmatched':
                if 'unassigned_chain' not in step_errors:
                    step_errors.append('unassigned_chain')
            chainset[component]['length'] = chain_length
        
        chains_key = awsKeyProvider().block_key(pdb_code, 'chains', 'info')
        s3.put(chains_key, chainset)
        peptide = None
        for chain in chainset:
            if chainset[chain]['best_match'] == 'peptide':
                peptide = {
                    'sequence':chainset[chain]['sequences'][0],
                    'molecule':chainset[chain]['molecule']
                }
        update = {}
        if peptide:
            update['peptide'] = peptide['sequence']
            data, success, errors = update_block(pdb_code, 'core', 'info', update, aws_config)
    return chainset, True, step_errors