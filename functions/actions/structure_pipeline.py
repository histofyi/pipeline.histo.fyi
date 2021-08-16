from ..histo import structureInfo
from ..pdb import RCSB
from ..lists import structureSet
from ..structure import split_assemblies, align_structure

from .sequence_pipeline import get_simplified_sequence_set

import logging

from functions.actions import sequence_pipeline
from functions.lists import structureSet

### Pipeline for categorising new structures
#
# Step 1 fetch PDB file and PDB info from RCSB
#
# Step 2 run automatic_assignment - this will result, if it fits into a common pattern with a set of assigned chain groups with alike chains grouped
#
# Step 2a if edge case, approve assignment or manually set assignment
#
# Step 3 run split_structure - this will result in a set of individual PDB files for each assembly
#
# Step 4 run align_structures - this will iterate through the split structures and create an aligned file for each
#
# Step 5 run match_structure - this will hopefully result in a match to a specific allele by sequence

sequence_sets = ['hla-a','hla-b','hla-c']




def clean_record(pdb_code):
    histo_info, success, errors = structureInfo(pdb_code).clean()
    data = {
        'histo_info': histo_info
    }
    return data, success, errors


def fetch_pdb_data(pdb_code):
    rcsb = RCSB()

    # gets the PDB file and the PDB info from RCSB
    pdb_file = rcsb.fetch(pdb_code)
    pdb_info = rcsb.get_info(pdb_code)

    # gets the initial histo_info file
    histo_info, success, errors = structureInfo(pdb_code).get()

    # create a dictionary of just the RCSB info we need
    rcsb_info = {}
    rcsb_info['primary_citation'] = pdb_info['rcsb_primary_citation']
    if 'pdbx_descriptor' in pdb_info['struct']:
        rcsb_info['description'] = ['pdbx_descriptor']
    rcsb_info['resolution_combined'] = pdb_info['rcsb_entry_info']['resolution_combined']
    rcsb_info['title'] = pdb_info['struct']['title']
    rcsb_info['assembly_count'] = pdb_info['rcsb_entry_info']['assembly_count']
    rcsb_info['pdb_code'] = pdb_code

    # persist it to the histo_info file
    histo_info, success, errors = structureInfo(pdb_code).put('rcsb_info', rcsb_info)

    data = {
        'histo_info': histo_info
    }

    return data, success, errors


def automatic_assignment(pdb_code):
    rcsb = RCSB()

    # gets the histo_info file with the RCSB data from Step 1
    histo_info, success, errors = structureInfo(pdb_code).get()

    # pull out the assembly count
    assembly_count = histo_info['rcsb_info']['assembly_count']

    # load the structure into BioPDB
    structure = rcsb.load_structure(pdb_code)

    try:
        # predict some initial chain assignments
        structure_stats = rcsb.predict_assigned_chains(structure, assembly_count)

        # get a set of the alike chains
        alike_chains = structure_stats['alike_chains']

        histo_info, success, errors = structureInfo(pdb_code).put('alike_chains', alike_chains)

        best_match = structure_stats['best_match']

        histo_info, success, errors = structureInfo(pdb_code).put('best_match', best_match)

        chain_assignments = structure_stats['chain_assignments']

        histo_info, success, errors = structureInfo(pdb_code).put('chain_assignments', chain_assignments)

        basic_info = structure_stats['basic_info']

        histo_info, success, errors = structureInfo(pdb_code).put('basic_info', basic_info)

        if best_match['confidence'] > 0.8:
            del structure_stats['complex_hits']
            data, success, errors = structureSet(best_match['best_match']).add(pdb_code)
        elif best_match['confidence'] > 0.5:
            data, success, errors = structureSet('probable_' + best_match['best_match']).add(pdb_code)
        else:
            data, success, errors = structureSet('unmatched').add(pdb_code)

        data, success, errors = structureSet('automatically_matched').add(pdb_code)

    except:
        data, success, errors = structureSet('error').add(pdb_code)

    data = {
            'histo_info': histo_info
    }
    return data, success, errors


def split_structure(pdb_code):
    histo_info, success, errors = structureInfo(pdb_code).get()
    current_assembly = RCSB().load_structure(pdb_code)
    split_information = split_assemblies(histo_info, current_assembly, pdb_code)
    histo_info, success, errors = structureInfo(pdb_code).put('split_info', split_information)
    data = {
        'histo_info': histo_info
    }
    return data, success, errors


def align_structures(pdb_code):
    histo_info, success, errors = structureInfo(pdb_code).get()
    align_info = {}
    mhc_alpha_chains = []
    #mhc_beta_chains = []
    aligned_assignment = ''
    for chain in histo_info['chain_assignments']:
        if 'class_i_alpha' in histo_info['chain_assignments'][chain]['label']:
            logging.warn('CLASS I ALPHA FOUND')
            mhc_alpha_chains = histo_info['chain_assignments'][chain]['chains']
            aligned_assignment = 'class_i_alpha'
    errors = []
    if 'split_info' in histo_info:
        logging.warn("HAS SPLIT INFO")
        i = 1
        for complex in histo_info['split_info']['complexes']:
            logging.warn(complex)
            for chain in mhc_alpha_chains:
                logging.warn(chain)
                if chain in complex['chains']:
                    complex_number = 'complex_' + str(i)
                    current_alignment = {
                        'aligned_chain': chain,
                        'chain_assignment': aligned_assignment,
                        'filename': complex['filename']
                    }
                    if True:
                        align_information = align_structure('class_i', pdb_code, str(i), chain)
                        if align_information:
                            current_alignment['rms'] = align_information
                        else:
                            current_alignment['errors'] = ['unable_to_load']
                    else:
                        current_alignment['errors'] = ['unable_to_align']
                    align_info[complex_number] = current_alignment
            i += 1
        histo_info, success, errors = structureInfo(pdb_code).put('align_info', align_info)  
    else:
        align_info = {'error':'structure_not_split'}  
    data = {
        'histo_info': histo_info
    }
    return data, success, errors


def first_pass_sequence_match(sequence_to_test):
    match_info = None
    for locus in sequence_sets:
        locus_set, success, errors = get_simplified_sequence_set('class_i', locus)
        for allele_group in  locus_set['sequences']:
            this_sequence = locus_set['sequences'][allele_group]['alleles'][0]['sequence']
            if sequence_to_test == this_sequence:
                match_info = {
                    'allele': locus_set['sequences'][allele_group]['alleles'][0]['allele'],
                    'allele_group': locus_set['sequences'][allele_group]['alleles'][0]['allele_group'],
                    'locus':locus,
                    'confidence': 1
                }
                break
        if match_info:
            break
    return match_info
    

def second_pass_sequence_match(sequence_to_test):
    match_info = None
    for locus in sequence_sets:
        locus_set, success, errors = get_simplified_sequence_set('class_i', locus)
        for allele_group in  locus_set['sequences']:
            allele_set = locus_set['sequences'][allele_group]['alleles']
            for allele in allele_set:
                this_sequence = allele['sequence']
                if sequence_to_test == this_sequence:
                    match_info = {
                        'allele': allele['allele'],
                        'allele_group': allele['allele_group'],
                        'locus':locus,
                        'confidence': 1
                    }
                    break
        if match_info:
            break
    return match_info


def match_structure(pdb_code):
    histo_info, success, errors = structureInfo(pdb_code).get()
    has_class_i_alpha = False
    match_info = None
    if 'best_match' in histo_info:
        if 'class_i' in histo_info['best_match']['best_match'] and histo_info['best_match']['confidence'] > 0.9:
            has_class_i_alpha = True
    elif 'complex_type' in histo_info:
        if 'class_i' in histo_info['complex_type']:
            has_class_i_alpha = True
    if has_class_i_alpha:
        sequence_to_test = histo_info['chain_assignments']['class_i_alpha']['sequences'][0]
        if len(sequence_to_test) > 275:
            sequence_to_test = sequence_to_test[0:275]
        match_info = first_pass_sequence_match(sequence_to_test)
        if not match_info:
            match_info = second_pass_sequence_match(sequence_to_test)
    if match_info:
        logging.warn("MATCH")
        logging.warn(match_info)
        histo_info, success, errors = structureInfo(pdb_code).put('match_info', match_info)
        data, success, errors = structureSet('alleles/human/all').add(pdb_code)
        data, success, errors = structureSet('alleles/human/'+ match_info['locus'] + '/all').add(pdb_code)
        data, success, errors = structureSet('alleles/human/'+ match_info['locus'] + '/' + match_info['allele_group'].replace('*','')).add(pdb_code)
        data, success, errors = structureSet('alleles/human/'+ match_info['locus'] + '/' + match_info['allele'].replace(':','_').replace('*','')).add(pdb_code)
    else:
        data, success, errors = structureSet('alleles/nomatch').add(pdb_code)
    data = {
        'histo_info': histo_info
    }
    return data, True, None


def peptide_positions(pdb_code):
    pass


