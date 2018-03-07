#!/bin/python2
#
#   db.py
#
#   SQLObject database definition for accountz.


import sys, md5, os
from sqlobject import *
from datetime import date, datetime, timedelta


# Create connection
#//connection = connectionForURI('postgres://localhost/datamind_accounts')
connection = connectionForURI('sqlite://%s/kaempf.db' % os.getcwd())
sqlhub.processConnection = connection


# A ledger account
class Account(SQLObject):

    number = StringCol(length = 8)
    name = StringCol(length = 80)
    atype = StringCol(length = 1)

    # GL lines linked to this account
    lines = MultipleJoin('GL')

    numberIndex = DatabaseIndex('number')

    # Get the balance for an account (may want to cache this)
    def getBalance(self):
        n = 0.0
        for l in self.lines:
            n += l.debit - l.credit
        return n


# A transaction, consisting of multiple GL lines
class Trans(SQLObject):

    tdate = DateCol()
    #ref = StringCol(default = '')
    description = StringCol(default = '')
    #memo = StringCol(default = '')

    # GL lines linked to this account
    lines = MultipleJoin('GL')
    accounts = MultipleJoin('Account')

    dateIndex = DatabaseIndex('tdate')


# A general ledger entry, linking a transaction to an account
class GL(SQLObject):

    account = ForeignKey('Account', cascade = True)
    trans = ForeignKey('Trans', cascade = True)

    debit = FloatCol(default = 0)
    credit = FloatCol(default = 0)
    memo = StringCol(default = '')
    cleared = StringCol(length = 1, default = ' ')  # '*' or 'X' or blank

    acctIndex = DatabaseIndex('account')
    transIndex = DatabaseIndex('trans')


# Create tables, if 'create' on command line
if len(sys.argv) > 1 and sys.argv[1] == 'create':
    for t in [Account, Trans, GL]:
        print t
        t.createTable()
    


