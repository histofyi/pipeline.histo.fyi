from ..histo import structureInfo
from ..pdb import RCSB
from ..lists import structureSet

### Pipeline for categorising new structures
#
# Step 1 fetch PDB file and PDB info from RCSB
#
# Step 2 run automatic_assignment - this will result, if it fits into a common pattern with a set of assigned chain groups with alike chains grouped
#
# Step 3 if edge case, approve assignment or manually set assignment
#
# Step 4 run split_structure - this will result in a set of individual PDB files for each assembly
#
# Step 5 run align_assembly - this will iterate through the split structures
#
# Step 6 .... coming soon

def fetch_pdb_data(pdb_code):
    rcsb = RCSB()

    pdb_file = rcsb.fetch(pdb_code)
    pdb_info = rcsb.get_info(pdb_code)

    histo_info, success, errors = structureInfo(pdb_code).get()

    rcsb_info = {}
    rcsb_info['primary_citation'] = pdb_info['rcsb_primary_citation']
    rcsb_info['description'] = pdb_info['struct']['pdbx_descriptor']
    rcsb_info['resolution_combined'] = pdb_info['rcsb_entry_info']['resolution_combined']
    rcsb_info['title'] = pdb_info['struct']['title']
    rcsb_info['assembly_count'] = pdb_info['rcsb_entry_info']['assembly_count']
    rcsb_info['pdb_code'] = pdb_code
    histo_info, success, errors = structureInfo(pdb_code).put('rcsb_info', rcsb_info)

    data = {
        'histo_info': histo_info
    }

    return data, success, errors


def automatic_assignment(pdb_code):

    rcsb = RCSB()
    histo_info, success, errors = structureInfo(pdb_code).get()

    assembly_count = histo_info['rcsb_info']['assembly_count']

    structure = rcsb.load_structure(pdb_code)

    alike_chains = None
    if not alike_chains:

        structure_stats = rcsb.predict_assigned_chains(structure, assembly_count)

        alike_chains = rcsb.cluster_alike_chains(structure, assembly_count)
        
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

#    except:
#       data, success, errors = structureSet('error').add(pdb_code)

    data = {
            'histo_info': histo_info
    }
    return data, success, errors




def split_complexes():
    pass

def align_structures():
    pass



