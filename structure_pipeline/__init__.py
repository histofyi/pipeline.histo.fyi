from flask import Blueprint, current_app, request, redirect
from typing import Dict

from common.decorators import check_user, requires_privilege, templated
from common.models import itemSet
from common.forms import request_variables


# initial methods
from .pipeline_actions import test, view, initialise

from .pipeline_actions import assign_chains, assign_complex_type

# EMBL PDBe REST API methods
from .pipeline_actions import fetch_summary_info, fetch_publication_info, fetch_experiment_info, get_pdbe_structures

# EMBL-IPD data based methods
from .pipeline_actions import match_chains

# IEDB.org API based methods
from .pipeline_actions import api_match_peptide

# structure based methods (BioPython etc)
from .pipeline_actions import align_structures, peptide_neighbours, peptide_features, extract_peptides, measure_peptide_angles, measure_cleft_angles, measure_distances


import logging
import json


structure_pipeline_views = Blueprint('structure_pipeline_views', __name__)



def process_errors(errors_dict):
    minor_errors = []
    major_errors = []
    collated_errors = {
        'minor_errors_dict':{},
        'major_errors_dict':{},
        'by_pdb_code':{}
    }
    for pdb_code in errors_dict:
        if errors_dict[pdb_code] is not None:
            collated_errors['by_pdb_code'][pdb_code] = []
            for error in set(errors_dict[pdb_code]):
                collated_errors['by_pdb_code'][pdb_code].append(error)
            minor_errors.append(pdb_code)
            if not error in collated_errors['minor_errors_dict']:
                collated_errors['minor_errors_dict'][error] = []
            collated_errors['minor_errors_dict'][error].append(pdb_code)
    return collated_errors, minor_errors, major_errors





def roll_up_stats(errors_dict, members, success):
    collated_errors, minor_errors, major_errors = process_errors(errors_dict)
    stats = {
        'members':{'pdb_codes':members, 'count':0},
        'success':{'pdb_codes':success, 'count':0},
        'minor_errors':{'pdb_codes': minor_errors, 'count': 0},
        'major_errors':{'pdb_codes': major_errors, 'count': 0}
    }
    for item in stats:
        stats[item]['count'] = len(stats[item]['pdb_codes'])
    return stats, collated_errors




pipeline_actions = {
    'class_i': {
        'test':{'action':test, 'next':None, 'name':'Test', 'show_in_list':False, 'link':False},
        'view':{'action':view, 'next':None, 'name':'View', 'show_in_list':False, 'link':False},
        'initialise':{'action':initialise, 'name':'Initialise', 'show_in_list':False, 'link':False, 'next':'fetch_summary'},
        'fetch_summary':{'action':fetch_summary_info, 'name': 'Fetch summary', 'show_in_list':False, 'link':False, 'next':'fetch_structure'},
        'fetch_structure':{'action':get_pdbe_structures, 'name':'Fetch structure', 'show_in_list':False, 'link':False, 'next':'fetch_publications'},
        'fetch_publications':{'action':fetch_publication_info, 'name': 'Fetch publications', 'show_in_list':False, 'link':False, 'next':'fetch_experiment'},
        'fetch_experiment':{'action':fetch_experiment_info, 'name': 'Fetch experiment information', 'show_in_list':False, 'link':False, 'next':'assign_chains'},
        'assign_chains':{'action':assign_chains, 'name': 'Assign chains', 'show_in_list':False, 'link':False, 'next':'assign_complex_type'},
        'assign_complex_type':{'action':assign_complex_type, 'name': 'Assign complex type', 'show_in_list':False, 'link':False, 'next':'match_chains'},
        'match_chains':{'action':match_chains, 'name': 'Match to MHC sequences', 'show_in_list':False, 'link':False, 'next':'match_peptide'},
        'match_peptide':{'action':api_match_peptide, 'name': 'Match peptide', 'link':False, 'next':'align'},
        'align': {'action':align_structures, 'name': 'Align structures', 'link':False, 'next':'peptide_neighbours'},
        'peptide_neighbours': {'action':peptide_neighbours, 'name': 'Find peptide neighbours', 'link':False, 'next':'peptide_features'},
        'peptide_features': {'action':peptide_features, 'name': 'Define peptide features', 'link':False, 'next':'extract_peptides'},
        'extract_peptides': {'action':extract_peptides, 'name': 'Extract peptides', 'link':False, 'next':'measure_peptide_angles'},
        'measure_peptide_angles': {'action':measure_peptide_angles, 'name': 'Measure peptide angles', 'link':False, 'next':'measure_cleft_angles'},
        'measure_cleft_angles': {'action':measure_cleft_angles, 'name': 'Measure cleft angles', 'link':False, 'next':'measure_distances'},
        'measure_distances': {'action':measure_distances, 'name': 'Measure C alpha distances', 'link':False, 'next':'view'}

        # TODO re-implement/refactor these actions
#        'peptide_positions': {'action':peptide_positions, 'blocks':['peptide_positions']},
    },
    'class_ii': {}
}


@structure_pipeline_views.get('/')
@check_user
@requires_privilege('users')
@templated('structures/index')
def structure_home_handler(userobj:Dict) -> Dict:
    """
    This handler provides the homepage for the structure pipeline section

    Args: 
        userobj (Dict): a dictionary describing the currently logged in user with the correct privileges

    Returns:
        Dict: a dictionary containing the user object and a list of possible next actions

    """
    return {'userobj': userobj, 'actions':[]}


@structure_pipeline_views.post('/redirect')
@check_user
@requires_privilege('users')
def structure_redirect_handler(userobj:Dict) -> Dict:
    """
    This handler redirects to the individual structure pipeline for the PDB code requested, or to the multiple structure pipeline with the set requested

    Args: 
        userobj (Dict): a dictionary describing the currently logged in user with the correct privileges

    Returns:
        A redirect to the relevant starting point

    """
    variables = request_variables(None, params=['pdb_code','set_slug','set_context','mhc_class'])
    mhc_class = variables['mhc_class']
    if 'pdb_code' in variables:
        pdb_code = variables['pdb_code']
        url = f'/structures/{mhc_class.lower()}/initialise/{pdb_code.lower()}'
        return redirect(url)
    elif 'set_slug' in variables:
        set_slug = variables['set_slug']
        set_context = variables['set_context']
        url = f'/structures/{mhc_class.lower()}/initialise/set/{set_context.lower()}/{set_slug.lower()}'
        return redirect(url)
    else:
        return redirect('/pipeline/structures/')





@structure_pipeline_views.get('/<string:mhc_class>/<string:route>/set/<path:set_context>/<path:set_slug>')
@requires_privilege('users')
@templated('structures/set')
def pipeline_set_handler(userobj, mhc_class, route, set_context, set_slug):
    """
    This handler is used to perform structure pipeline actions on a set of structures en masse

    Args: 
        userobj (Dict): a dictionary describing the currently logged in user with the correct privileges
        mhc_class (str): a string describing the mhc_class that this set relates to, e.g. class_i
        route (str): the route to the action e.g. fetch_structure. This is the key in the pipeline_actions dictionary for that action
        slug (str): the slug for the set 

    Returns:
        Dict: a dictionary containing the user object, data aboutt the action performed and the next action in the pipeline

    """
    successes = []
    members = []
    errordict = {}
    itemset, success, errors = itemSet(set_slug, set_context).get()
    for pdb_code in itemset['members']:
        pdb_code = pdb_code.lower()
        members.append(pdb_code)
        data, success, errors = pipeline_actions[mhc_class][route]['action'](pdb_code, current_app.config['AWS_CONFIG'])
        if data:
            successes.append(pdb_code)
        if errors:
            errordict[pdb_code] = errors
    if pipeline_actions[mhc_class][route]['next']:
        next = pipeline_actions[mhc_class][route]['next']
        next_action = {
            'name': pipeline_actions[mhc_class][next]['name'],
            'slug': next
        }
    else:
        next_action = None
    stats, collated_errors = roll_up_stats(errordict, members, successes)
    if len(errordict) > 0:
        has_errors = True
    else:
        has_errors = False
    return {
        'stats':stats,
        'collated_errors':collated_errors,
        'has_errors':has_errors,
        'name':pipeline_actions[mhc_class][route]['name'], 
        'next_action':next_action, 
        'mhc_class':mhc_class, 
        'userobj': userobj,
        'set_name': itemset['metadata']['title'],
        'set_context': set_context,
        'set_slug': set_slug
    }


@structure_pipeline_views.get('/<string:mhc_class>/<string:route>/<string:pdb_code>')
@requires_privilege('users')
@templated('structures/item')
def pipeline_item_handler(userobj, mhc_class, route, pdb_code):
    """
    This handler is used to perform structure pipeline actions on a single named structure

    Args: 
        userobj (Dict): a dictionary describing the currently logged in user with the correct privileges
        mhc_class (str): a string describing the mhc_class that this set relates to, e.g. class_i
        route (str): the route to the action e.g. fetch_structure. This is the key in the pipeline_actions dictionary for that action
        pdb_code (str): the pdb_code for the structure
    Returns:
        Dict: a dictionary containing the user object, data aboutt the action performed and the next action in the pipeline

    """
    force = False
    if 'force' in request.args.to_dict():
        if request.args.get('force') == 'True':
            force = True
    data, success, errors = pipeline_actions[mhc_class][route]['action'](pdb_code.lower(), current_app.config['AWS_CONFIG'], force)

    if pipeline_actions[mhc_class][route]['next']:
        next = pipeline_actions[mhc_class][route]['next']
        next_action = {
            'name': pipeline_actions[mhc_class][next]['name'],
            'slug': next
        }
    else:
        next_action = None
    return {
            'data':data['action'],
            'core':data['core'], 
            'name':pipeline_actions[mhc_class][route]['name'], 
            'next':pipeline_actions[mhc_class][route]['next'], 
            'mhc_class':mhc_class, 
            'pdb_code':pdb_code, 
            'userobj':userobj, 
            'next_action':next_action,
            'errors':errors
    }


