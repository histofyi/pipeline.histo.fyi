from typing import Dict, List, Tuple


from common.providers import s3Provider, awsKeyProvider, PDBeProvider
from common.helpers import update_block, slugify

from common.models import itemSet


def fetch_experiment_info(pdb_code:str, aws_config:Dict, force:bool=False) -> Dict:
    """
    This function retrieves a fetches the experimental information from the PDBe REST API

    Args:
        pdb_code (str): the code of the PDB file
        aws_config (Dict): the AWS configuration for the environment
        force (bool): not currently used, may be implemented to force a re-download in the case of a revised structure
    """
    step_errors = []
    data = {'publication':None}
    try:
        experiment_info, success, errors = PDBeProvider(pdb_code).fetch_experiment()
    except:
        success = False
        experiment_info = None
        step_errors.append('unable_to_fetch_experimental_info')
    if experiment_info:
        update = {'crystallography':{}}
        if 'resolution' in experiment_info:
            update['resolution'] = experiment_info['resolution']
            
        else:
            update['resolution'] = None
            step_errors.append('no_resolution')
        if 'cell' in experiment_info:
            update['crystallography']['cell'] = experiment_info['cell']
        else:
            step_errors.append('no_cell')
        if 'spacegroup' in experiment_info:
            spacegroup = experiment_info['spacegroup']
            update['crystallography']['spacegroup'] = spacegroup
            set_title = f'{spacegroup} spacegroup'
            set_slug = slugify(set_title)
            set_description = f'Structures in {spacegroup} spacegroup'
            members = [pdb_code]
            itemset, success, errors = itemSet(set_slug, 'crystallographic').create_or_update(set_title, set_description, members, 'crystallographic')
        else:
            step_errors.append('no_spacegroup')
        if update['resolution'] is not None:
            string_resolution = str(update['resolution'])
            set_title = f'{string_resolution}&#8491; resolution'
            set_slug = slugify(set_title.replace('&#8491;', 'A'))
            set_description = f'Structures at {set_title}'
            members = [pdb_code]
            itemset, success, errors = itemSet(set_slug, 'resolution').create_or_update(set_title, set_description, members, 'resolution')
        data, success, errors = update_block(pdb_code, 'core', 'info', update, aws_config)
    output = {
            'action':{'experiment':experiment_info, 'source':'PDBe REST API experiment method'},
            'core':data
     }
    return output, success, step_errors
