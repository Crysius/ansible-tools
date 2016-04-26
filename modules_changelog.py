#!/usr/bin/env python

##########################################################################################
# A script to validate all new modules in the devel branch are in the CHANGELOG.md
##########################################################################################
#
#   EXAMPLE ...
#   [jtanner@ansidev scratch]$ ./modules_changelog.py ~/workspace/github/ansible/ansible
#   MODULE (azure_deployment) IS NOT IN THE 2.1 CHANGELOG!!!

import os
import sys
import subprocess
from optparse import OptionParser
from pprint import pprint

def run_command(cmd):
    p = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    (so, se) = p.communicate()
    return (p.returncode, so, se)


def list_module_files(dirpath):

    ''' Make a list of current modules in the checkout dir '''

    moduledir = os.path.join(dirpath, 'lib/ansible/modules')
    cmd = "find %s -type f -name '*.py'" % moduledir
    (rc, so, se) = run_command(cmd)
    files = [x.strip() for x in so.split('\n') if x.strip()]
    return files

def get_commits_for_files(dirpath, 
        paths=['lib/ansible/modules/core', 'lib/ansible/modules/extras']):

    ''' Associate a commitid to every file under given paths '''

    files = {}

    for path in paths:
        full_path = os.path.join(dirpath, path)
        files[full_path] = {}

        # use git to get commits with files added 
        cmd = "cd %s ; git log --name-status | egrep -e ^commit -e ^'A'" % full_path
        (rc, so, se) = run_command(cmd)

        lines = [x.strip() for x in so.split('\n') if x.strip()]
        commitid = None
        for idx,x in enumerate(lines):
            if x.strip().startswith('commit '):
                commitid = x.split()[1].strip()
            if x.strip().startswith('A\t'):
                thisfile = x.split('\t',1)[1].strip()
                files[full_path][thisfile] = commitid

    return files


def branches_for_commit(dirpath, commitid):

    ''' Return a list of branches for a commitid '''

    # http://stackoverflow.com/questions/1419623/how-to-list-branches-that-contain-a-given-commit
    # git branch --contains <commit>
    #print dirpath, commitid
    cmd = "cd %s; git branch -r --contains %s" % (dirpath, commitid)
    (rc, so, se) = run_command(cmd)
    branches = [x.strip() for x in so.split('\n') if x.strip()]
    branches = [x for x in branches if not x.startswith('*')]
    #pprint(branches)
    return branches


def parse_changelog(dirpath):

    ''' Convert changlog into a datastructure '''

    changelog = {}
    changelogfile = os.path.join(dirpath, 'CHANGELOG.md')

    fdata = None
    with open(changelogfile, 'rb') as f:
        fdata = f.read()
    lines = [x for x in fdata.split('\n') if x.strip()]

    thisversion = None
    thissection = None
    thismodule = None
    thismoduletopic = None
   
    #for idx, line in enumerate(lines[0:55]):
    for idx, line in enumerate(lines):
        if line.startswith('## '):
            thisversion = line.split()[1]
            
            changelog[thisversion] = {}
            changelog[thisversion]['newmodules'] = {}
            changelog[thisversion]['newmodules']['orphaned'] = []

        if line.startswith('####') and line[4] != '#':
            thissection = line.replace('####', '').replace(':', '').lower()

        ###########################################
        #   MODULES
        ###########################################
        if thissection == 'new modules':
            thismodule = None

            if line.strip().startswith('-'):
                # either a section or a module, depends on next line
                if lines[idx+1].strip().startswith('*'):
                    thismoduletopic = line.replace('-', '', 1).strip()
                else:
                    thismoduletopic = None
                    thismodule = line.replace('-', '', 1).strip()
            elif line.strip().startswith('*'):
                thismodule = line.replace('*', '').strip()

            if thismodule and not thismoduletopic:
                changelog[thisversion]['newmodules']['orphaned'].append(thismodule)
            elif thismodule and thismoduletopic:
                if not thismoduletopic in changelog[thisversion]['newmodules']:
                    changelog[thisversion]['newmodules'][thismoduletopic] = []
                changelog[thisversion]['newmodules'][thismoduletopic].append(thismodule)

    return changelog


def main():
    parser = OptionParser()
    #parser.add_option("-f", "--file", dest="filename",
    #                  help="write report to FILE", metavar="FILE")
    #parser.add_option("-q", "--quiet",
    #                  action="store_false", dest="verbose", default=True,
    #                  help="don't print status messages to stdout")
    (options, args) = parser.parse_args()
    #print options
    #print args

    dirpath = args[0]
    #print "dirpath: %s" % dirpath

    current_files = list_module_files(dirpath)

    changelog = parse_changelog(dirpath)
    ansible_versions = sorted(changelog.keys())
    ansible_devel_version = ansible_versions[-1]
    #pprint(ansible_versions)

    file_commits = get_commits_for_files(dirpath)
    for k,v in file_commits.iteritems():
        #print k
        for kfile,commitid in v.iteritems():
            if not kfile.endswith('.py'):
                continue
            fullpath = os.path.join(k, kfile)
            if '.' in os.path.basename(fullpath):
                fullpath = os.path.dirname(fullpath)
            if not os.path.isdir(fullpath) or (os.path.basename(kfile) == '__init__.py'):
                continue
            #print kfile,fullpath,commitid
            branches = branches_for_commit(fullpath, commitid)
            #pprint(branches)


            # check if commit only in devel and if in changelog
            non_devel_branches = [x for x in branches if not 'origin/devel' in x] 
            if len(non_devel_branches) == 0:
                #pprint(branches)
                module_name = os.path.basename(kfile).replace('.py', '')
                inchangelog = False
                for k,v in changelog[ansible_devel_version]['newmodules'].iteritems():
                    #print k,v
                    for vfile in v:
                        if vfile == module_name:
                            inchangelog = True
                            break
                    #import epdb; epdb.st()

                if not inchangelog:
                    print "MODULE (%s) IS NOT IN THE %s CHANGELOG!!!" % (module_name, ansible_devel_version)
            #import epdb; epdb.st()


if __name__ == "__main__":
    main()
