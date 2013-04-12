import re
import xml.etree.ElementTree as ET
import argparse

import requests 
from requests.auth import HTTPBasicAuth

import appscript
from appscript import k

class OmniFocus(object):
    path_separator = '////'
    
    def __init__(self):
        self.app = appscript.app('OmniFocus')
        self.doc = self.app.default_document
        
    def projects_in_folder(self, path):
        ## get specific folder
        folder = self.get_folder(path)
        
        return folder.projects.get()
        
    def flattened_projects_in_folder(self, path):
        folder = self.get_folder(path)
        
        return folder.flattened_projects.get()
        
    def flattened_folders_in_folder(self, path):
        folder = self.get_folder(path)
        
        return folder.flattened_folders.get()
        
    def projects_in_folder_with_name_matching_regex(self, path, regex):
        projects = self.projects_in_folder(path)
        
        matching_projects = []
        for p in projects:
            if re.search(regex, p.name.get()):
                matching_projects.append(p)
            
        return matching_projects
        
    def get_folder(self, path):
        paths = path.split(self.path_separator)
        paths.reverse()
        
        return self._recursive_get_folder(self.doc, paths)
        
    def create_folder(self, path):
        folder = self.doc
        
        for p in path.split(self.path_separator):
            if not folder.folders[p].exists():
                folder.make( new = k.folder, with_properties = { k.name: p })
            folder = folder.folders[p]
            
    def create_project_in_folder(self, path, name, note=''):
        folder = self.get_folder(path)
        
        if not folder.exists():
            self.create_folder(path)
            
        folder.make(
            new = k.project,
            with_properties = {
                k.name: name,
                k.note: note,
                }
        )
    
    def _recursive_get_folder(self, superfolder, subfolders):
        '''
        subfolders must be in reverse order, e.g. A/B/C would be ['C','B','A']
        '''

        folder = superfolder.folders[subfolders.pop()]

        if subfolders:
            folder = self._recursive_get_folder(folder, subfolders)
            
        return folder
        
        
class RedmineIssues(object):
    def __init__(self, issues_url, user, password, issues_url_prefix):
        self.issues_url = issues_url
        self.user = user
        self.password = password
        self.issues_url_prefix = issues_url_prefix
        
        self.issues = []
        
        self.refresh_issues()
        
    def refresh_issues(self):
        response = requests.get(self.issues_url, auth=HTTPBasicAuth(self.user, self.password))
        issue_xml = ET.fromstring(response.text)
        issues = []
        for i in issue_xml:
            issues.append(
                {
                    'id' : i.find('id').text,
                    'url' : '%s/%s' % (self.issues_url_prefix, i.find('id').text),
                    'project' : i.find('project').attrib['name'],
                    'tracker' : i.find('tracker').attrib['name'],
                    'status' : i.find('status').attrib['name'],
                    'author' : i.find('author').attrib['name'],
                    'assigned_to' : i.find('assigned_to').attrib['name'],
                    'subject' : i.find('subject').text,
                    'description' : i.find('description').text,
                }
            )
            
        self.issues = issues

def omnifocus_project_from_redmine_issue(omnifocus_projects, redmine_issue):
    issue_id_string = '#%s' % redmine_issue['id']
    
    project = None
    for p in omnifocus_projects:
        if re.search(r'^%s' % issue_id_string, p.name.get()):
            project = p
            break
    
    return project
    
def redmine_issue_from_omnifocus_project(redmine_issues, omnifocus_project):
    match = re.search(r'^#(\d+) ', omnifocus_project.name.get())
    issue_id = match.group(1)
    
    issue = None
    for i in redmine_issues:
        if i['id'] == issue_id:
            issue = i

    return issue

def omnifocus_note_from_redmine_issue(issue):
    project_note = \
'''%s

Status: %s
Project: %s
Author: %s
Assigned To: %s

%s''' % (
            issue['url'],
            issue['status'],
            issue['project'],
            issue['author'],
            issue['assigned_to'],
            issue['description'],
        )
    
    return project_note

def omnifocus_project_name_from_redmine_issue(issue):
    project_name = '#%s - %s' % (issue['id'], issue['subject'])
    
    return project_name
    
def sync_redmine_and_omnifocus(omnifocus_folder, redmine_url, redmine_user, redmine_password, redmine_issues_url_prefix):
    rmi = RedmineIssues(redmine_url, redmine_user, redmine_password, redmine_issues_url_prefix)
    of = OmniFocus()
    
    # delete missing projects
    extant_redmine_issue_ids = [ i['id'] for i in rmi.issues ]
    for i in of.flattened_projects_in_folder(omnifocus_folder):
        match = re.search(r'^#(\d+) ', i.name.get())
        if not match:
            i.delete()
        else:
            issue_id = match.group(1)
            if not issue_id in extant_redmine_issue_ids:
                i.delete()

    # delete missing folders
    extant_redmine_projects = [ i['project'] for i in rmi.issues ]
    for f in of.flattened_folders_in_folder(omnifocus_folder):
        if not f.name.get() in extant_redmine_projects:
            f.delete()

    # update existing projects
    for p in of.flattened_projects_in_folder(omnifocus_folder):
        redmine_issue = redmine_issue_from_omnifocus_project(rmi.issues, p)
        
        p.note.set(omnifocus_note_from_redmine_issue(redmine_issue))
        p.name.set(omnifocus_project_name_from_redmine_issue(redmine_issue))

    # create new projects
    for issue in rmi.issues:
    
        if not omnifocus_project_from_redmine_issue(of.flattened_projects_in_folder(omnifocus_folder), issue):
            project_path = omnifocus_folder + of.path_separator + issue['project']
            
            project_name = omnifocus_project_name_from_redmine_issue(issue)
            project_note = omnifocus_note_from_redmine_issue(issue)

            of.create_project_in_folder(
                path = project_path,
                name = project_name,
                note = project_note
            )
            
    of.doc.synchronize()
    
def main():
    parser = argparse.ArgumentParser(description = \
'''One way sync from Redmine to Omnifocus. Will not attempt to sync unless OmniFocus is running.

Note that for some Redmine installations invalid credentials will result in an empty issues list instead of an error.''')
    
    parser.add_argument('omnifocus_folder', type=str, help='Name of the folder in which Redmine issues will be written.  Path separator is %s' % OmniFocus.path_separator)
    parser.add_argument('redmine_issues_url', type=str, help='URL from which Redmine issues will be pulled.  XML output is required.  http://$YOURHOST/redmine/issues.xml?assigned_to_id=me is probably what you want.')
    parser.add_argument('redmine_issues_url_prefix', type=str, help='A url fragment that is used to construct issue links.  e.g. for issue 1234 and redmine_issues_url_prefix http://localhost/redmine/issues, the issue link will be http://localhost/redmine/issues/1234.')
    parser.add_argument('redmine_user', type=str, help='Username used to login to Redmine.')
    parser.add_argument('redmine_password', type=str, help='Password used to login to Redmine.')    
    
    args = parser.parse_args()
    
    of = appscript.app('OmniFocus')
    if of.isrunning():
        sync_redmine_and_omnifocus(args.omnifocus_folder, args.redmine_issues_url, args.redmine_user, args.redmine_password, args.redmine_issues_url_prefix)
#        sync_redmine_and_omnifocus('DreamBox////Redmine', 'http://redmine/redmine/issues.xml?assigned_to_id=me', 'adamsb6','rh739zf!', 'http://redmine/redmine/issues')
        
if __name__ == "__main__":
    main()