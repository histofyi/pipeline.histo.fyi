from flask import Blueprint, current_app, request

from common.decorators import check_user, requires_privilege, templated

from .pipeline_actions import list_constants, view_constants, upload_constants, view_item

import logging
import json

constants_views = Blueprint('constants_views', __name__)



pipeline_actions = {
        'list':{'action':list_constants,'next':None, 'name':'List constants', 'slug':'list', 'show_in_list':True, 'link':True},
        'view':{'action':view_constants,'next':None, 'name':'View constants', 'slug':'view', 'show_in_list':True, 'link':True},
        'upload':{'action':upload_constants,'next':None, 'name':'Upload constants', 'slug':'upload', 'show_in_list':True, 'link':False},
}


@constants_views.get('/')
@check_user
@requires_privilege('users')
@templated('constants/index')
def constants_home_handler(userobj):
    return {'userobj': userobj, 'actions':[pipeline_actions[action] for action in pipeline_actions]}



@constants_views.get('/<string:route>/<string:slug>')
@check_user
@requires_privilege('users')
@templated('constants/item')
def pipeline_view_item_handler(userobj, route, slug):
    data, success, errors = view_item(current_app.config['AWS_CONFIG'], slug)
    return {
        'item':data, 
        'next':pipeline_actions[route]['next'], 
        'action':pipeline_actions[route]['name'], 
        'link':pipeline_actions[route]['link'], 
        'success': success, 
        'errors':errors, 
        'action':route, 
        'section':'constants',
        'items':'constants'
    }




@constants_views.get('/<string:route>')
@check_user
@requires_privilege('users')
@templated('constants/multiple')
def pipeline_handler(userobj, route):
    data, success, errors = pipeline_actions[route]['action'](current_app.config['AWS_CONFIG'])
    if route == 'list':
        fullview = False
    else:
        fullview = True
    return {
        'data':data, 
        'next':pipeline_actions[route]['next'], 
        'action':pipeline_actions[route]['name'], 
        'link':pipeline_actions[route]['link'], 
        'success': success, 
        'errors':errors, 
        'action':route, 
        'section':'constants',
        'items':'constants',
        'fullview': fullview 
    }



