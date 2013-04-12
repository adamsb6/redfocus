redfocus
========

This utility creates projects in OmniFocus based on issues contained in XML consumed from Redmine.

Redmine issues are consumed from an arbitrary URL, allowing users to construct a custom query for
their desired issues.  For example, a user could create a Redmine query that pulls only new 
issues assigned to the user or the user's team.

Installation
============

::

$ sudo python setup.py install

Usage
=====

::

    usage: redfocus [-h]
                                omnifocus_folder redmine_issues_url
                                redmine_issues_url_prefix redmine_user
                                redmine_password

    One way sync from Redmine to Omnifocus. Will not attempt to sync unless
    OmniFocus is running. Note that for some Redmine installations invalid
    credentials will result in an empty issues list instead of an error.

    positional arguments:
      omnifocus_folder      Name of the folder in which Redmine issues will be
                            written. Path separator is ////
      redmine_issues_url    URL from which Redmine issues will be pulled. XML
                            output is required.
                            http://$YOURHOST/redmine/issues.xml?assigned_to_id=me
                            is probably what you want.
      redmine_issues_url_prefix
                            A url fragment that is used to construct issue links.
                            e.g. for issue 1234 and redmine_issues_url_prefix
                            http://localhost/redmine/issues, the issue link will
                            be http://localhost/redmine/issues/1234.
      redmine_user          Username used to login to Redmine.
      redmine_password      Password used to login to Redmine.

    optional arguments:
      -h, --help            show this help message and exit