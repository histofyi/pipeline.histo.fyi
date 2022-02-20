from ..providers import filesystemProvider
import json
import datetime

import logging


file = filesystemProvider(None)

class structureSet():

    setname = None
    default_structure = {
                            "last_updated":None,
                            "set": []
                        }

    def __init__(self, setname):
        self.setname = setname


    def build_set_path(self):
        path = 'sets/structures/{setname}'.format(setname = self.setname)
        return path


    def check_exists(self):
        exists = file.check_exists(self.build_set_path())
        return exists


    def add(self, item):
        structureset, success, errors = self.get()
        try:
            structureset = json.loads(structureset)
        except:
            structureset = structureset
        
        if item not in structureset['set']:
            structureset['set'].append(item)
            structureset['last_updated'] = datetime.datetime.now().isoformat()
            structureset, success, errors = file.put(self.build_set_path(), json.dumps(structureset))
        return structureset, success, errors


    def put(self, set, force=False):
        structureset, success, errors = self.get()
        try:
            structureset = json.loads(structureset)
        except:
            structureset = structureset
        
        if len(structureset['set']) == 0 or force == True:
            structureset['set'] = set
            structureset['last_updated'] = datetime.datetime.now().isoformat()
            structureset['length'] = len(set)
            structureset, success, errors = file.put(self.build_set_path(), json.dumps(structureset))
        else:
            errors.append('structureset_already_has_members')
        return structureset, success, errors    


    def get(self):
        structureset, success, errors = file.get(self.build_set_path())
        if not structureset:
            payload = self.default_structure
            payload['last_updated'] = datetime.datetime.now().isoformat()
            structureset, success, errors = file.put(self.build_set_path(), json.dumps(payload))
        structureset['length'] = len(structureset['set'])
        structureset['ui_text'] = self.setname.replace('_',' ').title()
        structureset['slug'] = self.setname
        structureset['last_updated'] = datetime.datetime.fromisoformat(structureset['last_updated'])
        return structureset, success, errors


    def remove(self, item):
        pass
    