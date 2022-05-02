from flask import Blueprint, current_app, request, redirect
from typing import Dict

from common.decorators import check_user, requires_privilege, templated
from common.models import itemSet

from common.forms import request_variables, validate_variables
from common.helpers import slugify


import logging
import json

from .pipeline_actions import process_pdbefold

set_pipeline_views = Blueprint('set_pipeline_views', __name__)


contexts = ["complex_type", "similarity", "differences", "publication", "features", "chronology", "crystallography", "species", "resolution", "locus", "allele", "allele_group", "peptide_sequence", "peptide_length", "peptide_cluster", "peptide_features", "search_query", "matching", "testing","errors"]


@set_pipeline_views.get('/')
@check_user
@requires_privilege('users')
@templated('sets/index')
def sets_home_handler(userobj:Dict) -> Dict:
    """
    This handler provides the homepage for the sets pipeline section

    Args: 
        userobj (Dict): a dictionary describing the currently logged in user with the correct privileges

    Returns:
        Dict: a dictionary containing the user object and a list of possible next actions

    """
    return {'userobj': userobj, 'actions':[]}


@set_pipeline_views.get('/create')
@check_user
@requires_privilege('users')
@templated('sets/create')
def sets_create_form_handler(userobj:Dict) -> Dict:
    """
    This handler provides the form for editorial set curation

    Args: 
        userobj (Dict): a dictionary describing the currently logged in user with the correct privileges

    Returns:
        Dict: a dictionary containing the user object, an empty variables dictionary and an errors array containing the indication that it's an empty form

    """
    return {'userobj': userobj, 'variables':{}, 'errors':['blank_form'], 'contexts':contexts}


@set_pipeline_views.post('/create')
@check_user
@requires_privilege('users')
@templated('sets/create')
def sets_create_action_handler(userobj:Dict) -> Dict:
    """
    This handler provides the action for editorial set curation

    variables (Dict): retrieved from the form


    Args: 
        userobj (Dict): a dictionary describing the currently logged in user with the correct privileges

    Returns:
        Dict: a dictionary containing the user object and either variables and errors, or a redirect to a "next steps" page

    """
    params = ['title','description','members','context']
    itemset = None
    success = False
    errors = []

    variables = request_variables(None, params=params)
    validated, errors = validate_variables(variables, params)
    if validated:
        set = itemSet(None, variables['context'], title=variables['title'])
        if set.exists():
            errors = ['set_already_exists']
            return {'userobj': userobj, 'variables':variables, 'validated': validated, 'errors':errors, 'success':success, 'itemset':itemset, 'contexts':contexts}
        else:
            if variables['members'] is not None:
                variables['members'] = set.clean_members(variables['members'])
            itemset, success, errors = set.create(variables['title'], variables['description'], variables['members'], variables['context'])
            set_slug = itemset['metadata']['slug']
            set_context = itemset['context']
            redirect_to = f'/sets/create/complete/{set_context}/{set_slug}'
            return {'redirect_to': redirect_to}
    else:
        errors = ['validation_errors']
        return {'userobj': userobj, 'variables':variables, 'validated': validated, 'errors':errors, 'success':success, 'itemset':itemset, 'contexts':contexts}


@set_pipeline_views.get('/view/<string:set_context>/<string:set_slug>')
@check_user
@requires_privilege('users')
@templated('sets/view')
def set_view(userobj:Dict, set_context:str, set_slug:str) -> Dict:
    """
    This handler provides the form for changing the members of a set, adding or removing

    Args: 
        userobj (Dict): a dictionary describing the currently logged in user with the correct privileges

    Returns:
        Dict: a dictionary containing the user object, an empty variables dictionary and an errors array containing the indication that it's an empty form

    """
    variables = request_variables(None, params=['page_number'])
    if variables['page_number'] is not None :
        page_number = int(variables['page_number'])
    else:
        page_number = 1
    set_slug = slugify(set_slug)
    set_context = slugify(set_context)
    itemset, success, errors = itemSet(set_slug, set_context).get(page_number=page_number, page_size=25)    
    return {'userobj': userobj, 'itemset':itemset}


@set_pipeline_views.get('/<string:action>/complete/<string:set_context>/<string:set_slug>')
@check_user
@requires_privilege('users')
@templated('sets/action_complete')
def sets_create_complete_handler(userobj:Dict, action:str, set_context:str, set_slug:str) -> Dict:
    """
    This handler provides the confirmation page for editorial set curation

    variables (Dict): retrieved from the form


    Args: 
        userobj (Dict): a dictionary describing the currently logged in user with the correct privileges


    Returns:
        Dict: a dictionary containing the user object and a list of possible next actions

    """
    itemset, success, errors = itemSet(set_slug, set_context).get()
    return {'userobj': userobj, 'itemset':itemset, 'action':action}


@set_pipeline_views.get('/<string:action>/<string:set_context>/<string:set_slug>')
@check_user
@requires_privilege('users')
@templated('sets/add_remove_members')
def sets_add_remove_form_handler(userobj:Dict, action:str, set_slug:str) -> Dict:
    """
    This handler provides the form for changing the members of a set, adding or removing

    Args: 
        userobj (Dict): a dictionary describing the currently logged in user with the correct privileges

    Returns:
        Dict: a dictionary containing the user object, an empty variables dictionary and an errors array containing the indication that it's an empty form

    """
    itemset, success, errors = itemSet(set_slug).get()    
    variables = {}
    return {'userobj': userobj, 'variables':{}, 'action':action, 'itemset':itemset}



@set_pipeline_views.post('/<string:action>/<string:set_context>/<string:set_slug>')
@check_user
@requires_privilege('users')
@templated('sets/add_remove_members')
def sets_add_remove_action_handler(userobj:Dict, action:str, set_context:str, set_slug:str) -> Dict:
    """
    This handler provides the action for changing the members of a set, adding or removing

    variables (Dict): retrieved from the form

    Args: 
        userobj (Dict): a dictionary describing the currently logged in user with the correct privileges

    Returns:
        Dict: a dictionary containing the user object, an empty variables dictionary and an errors array containing the indication that it's an empty form

    """
    itemset, success, errors = itemSet(set_slug, set_context).get()
    success = True    
    variables = request_variables(None, params=['members'])
    if ',' in variables['members']:
        members = itemSet(set_slug).clean_members(variables['members'])
    elif len(variables['members']) == 4:
        members = [variables['members']]
    else:
        success = False
    logging.warn(members)
    if success:
        if action == 'add':
            itemset, success, errors = itemSet(set_slug).add_members(members)
        else:
            itemset, success, errors = itemSet(set_slug).remove_members(members)
        redirect_to = f'/sets/{action}/complete/{set_slug}'
        return {'redirect_to': redirect_to}
    else:
        return {'userobj': userobj, 'variables':variables, 'action':action, 'itemset':itemset}





@set_pipeline_views.get('/alter/<string:set_context>/<string:set_slug>')
@check_user
@requires_privilege('users')
@templated('sets/alter')
def sets_alter_form_handler(userobj:Dict, set_context:str, set_slug:str) -> Dict:
    """
    This handler provides the form for changing the metadata of a set

    Args: 
        userobj (Dict): a dictionary describing the currently logged in user with the correct privileges

    Returns:
        Dict: a dictionary containing the user object and a list of possible next actions

    """
    params = ['title','description','members','context']
    itemset = None
    success = False
    errors = []
    return {'userobj': userobj, 'variables':{}, 'errors':['blank_form']}


@set_pipeline_views.get('/alter/<string:set_context>/<string:set_slug>')
@check_user
@requires_privilege('users')
@templated('sets/alter')
def sets_alter_action_handler(userobj:Dict) -> Dict:
    """
    This handler provides the action for changing the metadata of a set

    variables (Dict): retrieved from the form

    Args: 
        userobj (Dict): a dictionary describing the currently logged in user with the correct privileges

    Returns:
        Dict: a dictionary containing the user object and a list of possible next actions

    """
    params = ['title','description','members','context']
    itemset = None
    success = False
    errors = []
    return {'userobj': userobj, 'variables':{}, 'errors':['blank_form']}



@set_pipeline_views.get('/process/pdbefold/<string:mhc_class>')
@check_user
@requires_privilege('users')
@templated('sets/process')
def sets_process_handler(userobj:Dict, mhc_class:str) -> Dict:
    """
    This handler returns an itemset of molecules found using the PDBeFold service

    Args: 
        userobj (Dict): a dictionary describing the currently logged in user with the correct privileges
        mhc_clas (str): the class of MHC molecule being searched for

    Returns:
        Dict: a dictionary containing the user object and a an itemset for that particular class of MHC molecules

    """
    itemset = process_pdbefold(mhc_class)
    return {'userobj': userobj, 'itemset': itemset}


