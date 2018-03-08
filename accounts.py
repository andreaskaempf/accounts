#!/usr/bin/python2

import socket, json, time
from cStringIO import StringIO
import cherrypy as cp
from datetime import datetime, date
from db import *

account_types = { 'A' : 'Asset', 'L' : 'Liability', 'I' : 'Income', 'E' : 'Expense' }

class Main:

    @cp.expose
    def index(self, **args):
        raise cp.HTTPRedirect('/accounts')

    # List all accounts
    @cp.expose
    def accounts(self, **args):

        s = StringIO()
        header(s, 'accounts')
        s.write('<h1>Accounts</h1>\n')

        s.write('<table class="table table-striped table-bordered">\n')
        th(s, ['Account', 'Transactions', 'Balance'])

        tot = 0.0
        prevType = ''
        for a in Account.select(orderBy = ['atype', 'name']):
            if a.atype != prevType:
                s.write('<tr><td colspan=3 style="font-size: 1.2em; font-weight: bold; background-color: #ccc">%s</td></tr>\n' % account_types[a.atype])
                prevType = a.atype
            s.write('<tr>\n')
            s.write(' <td><a href="/account?id=%d">%s</a>\n' % (a.id, a.name))
            s.write(' <a href="/edit_account?id=%d"><img src="/static/edit.gif"/></a></td>\n' % a.id)
            s.write(' <td>%d</td>\n' % len(a.lines))
            s.write(' <td style="text-align: right">%.2f</td>\n' % a.getBalance())
            s.write('</tr>\n')

        # Total row
        s.write('<tr style="font-weight: bold"><td colspan="2">Total:</td><td style="text-align:right">%.2f</td></tr>\n' % tot)
        s.write('</table>\n')

        # Buttons to add account or transaction
        s.write('<p><a href="/edit_account" class="btn btn-primary btn-sm">Add an account</a> &nbsp; \n')
        s.write('<a href="/transactions">All transactions</a></p>\n')

        footer(s)
        return s.getvalue()


    # Edit/create an account
    @cp.expose
    def edit_account(self, **args):

        # Get the account id and the account, none means new
        try:
            aid = int(args.get('id',0))
            a = Account.get(aid) if aid else None
        except Exception, e:
            return 'Could not get account: ' + e.message

        # Save changes
        errs = []
        if cp.request.method == 'POST':
            nm = args['name'].strip()
            no = args['number'].strip()
            t = args['type']
            if len(nm) == 0 or len(no) == 0:
                errs.append('Please enter both name and number')

            if len(errs) == 0:
                if a:
                    a.set(number = no, name = nm, atype = t)
                else:
                    Account(number = no, name = nm, atype = t)
                raise cp.HTTPRedirect('/accounts')

        # Start page, with form
        s = StringIO()
        header(s, 'accounts')
        s.write('<h1>%s Account</h1>\n' % ('Edit' if a else 'New'))

        if cp.request.method == 'POST':
            nm = args['name']
            no = args['number']
            tp = args['type']
        elif a:
            nm = a.name
            no = a.number
            tp = a.atype
        else:
            nm = no = ''
            tp = 'E'

        for e in errs:
            s.write('<p class="alert alert-danger">%s</p>\n' % e)
        s.write('<form action="edit_account" method="post">\n')
        s.write('<input type="hidden" name="id" value="%d" />\n' % aid)
        s.write('<p><b>Number:</b> <input type="text" name="number" value="%s" /></p>\n' % no)
        s.write('<p><b>Name:</b> <input type="text" name="name" value="%s" /></p>\n' % nm)
        s.write('<p><b>Type:</b> ')
        for t in account_types.keys():
            ck = 'checked="checked"' if t[0] == tp else ''
            s.write('<input type="radio" name="type" value="%s" %s /> %s ' % (t, ck, account_types[t]))
        s.write('</p>\n')
        s.write('<p><input type="submit" value="%s" class="btn btn-primary btn-sm" /></p>\n' % ('Save changes' if a else 'Create account'))
        s.write('</form>\n')

        footer(s)
        return s.getvalue()


    # List all transactions for one account
    @cp.expose
    def account(self, **args):

        # Get account
        try:
            aid = int(args['id'])
            a = Account.get(aid)
        except Exception, e:
            return 'Account not found: ' + e.message

        # Remember account ID in session
        cp.session['account'] = aid

        # Start page, with buttons to add transaction and to reconcile
        s = StringIO()
        header(s, 'accounts')
        s.write('<h1>%s ' % a.name)
        s.write('<a href="/qtransaction?aid=%d" class="btn btn-primary btn-xs">Add Transaction</a>\n' % aid)

        # Get status of reconciliation, and show button if not currently reconciling
        if 'reconcile' in args:
            cp.session['reconcile'] = 1
        reconciling = 'reconcile' in cp.session
        if not reconciling:
            s.write('<a href="/account?id=%d&reconcile=1" class="btn btn-primary btn-xs">Reconcile</a>\n' % aid)
        s.write('</h1>\n')

        # Get all the transaction lines in a list, sorted by date
        ll = list(a.lines)
        ll.sort(lambda a,b: cmp(a.trans.tdate, b.trans.tdate))

        # If reconciling, show box at top
        if reconciling:

            # Do the math
            prCleared = cleared = 0.    # get from data, status 'X' or '*'
            for l in ll:
                if l.cleared == 'X':
                    prCleared += (l.debit - l.credit)
                elif l.cleared == '*':
                    cleared += (l.debit - l.credit)
            stmtBal = cp.session.get('reconcile_stmt_bal', 0.) # user input
            diff = stmtBal - (prCleared + cleared)

            # Embed the values in Javascript, so the event handlers can update them
            s.write('<script type="text/javascript">\n')
            s.write('var pr_cleared = %f, cleared = %f, stmt_bal = %f;' % (prCleared, cleared, stmtBal));
            s.write('</script>\n')

            # Show values in box
            s.write('<div id="reconcile">\n')
            s.write('<p><b>Reconciliation</b> : \n')
            s.write('Statement final balance = <input type="text" value="%.2f" onchange="reconcileSetStmtBal(event)" /></p>\n' % stmtBal)
            s.write('<p>Prev cleared <span class="greyfield" id="pr_cleared">%.2f</span>\n' % prCleared)
            s.write('+ new cleared <span class="greyfield" id="cleared">%.2f</span>\n' % cleared)
            s.write('= total cleared <span class="greyfield" id="tot_cleared">%.2f</span> ==&gt;\n' % (prCleared + cleared))
            s.write('<span class="greyfield" id="diff">%.2f</span> difference</p>\n' % diff)
            s.write('</p>\n')
            s.write('<p><a href="/finishReconciliation" class="btn btn-sm btn-primary" enabled=false>Done</a>\n')
            s.write('<a href="/finishReconciliation?cancel=1" class="btn btn-sm btn-danger">Cancel</a></p>\n')
            s.write('</div>\n')

        # Show table of transactions, most recent at the bottom (to allow for easy running balance)
        s.write('<table class="table table-striped table-bordered">\n')
        th(s, ['Date', 'Description', '*', 'Debit', 'Credit', 'Balance'])
        bal = 0
        for l in ll:

            t = l.trans
            dr = l.debit
            cr = l.credit
            bal += (dr - cr)

            s.write('<tr>\n')
            tdate = format_date(t.tdate)
            s.write(' <td>%s <a href="/qtransaction?aid=%d&tid=%d"><img src="/static/edit.gif"/></a></td>\n' % (tdate, aid, t.id))
            s.write(' <td>%s</td>\n' % t.description)
            if reconciling and l.cleared != 'X':
                ck = 'checked' if l.cleared == '*' else ''
                s.write(' <td><input type="checkbox" id="clear%d" %s onchange="checkReconcile(event)" /></td>\n' % (l.id, ck))
            else:
                s.write(' <td>%s</td>\n' % l.cleared)
            s.write(' <td style="text-align: right">%s</td>\n' % ('' if dr == 0.0 else '%.2f' % dr))
            s.write(' <td style="text-align: right">%s</td>\n' % ('' if cr == 0.0 else '%.2f' % cr))
            s.write(' <td style="text-align: right">%.2f</td>\n' % bal)
            s.write('</tr>\n')

        s.write('</table>\n')

        s.write('<p><a href="/qtransaction?aid=%d" class="btn btn-primary btn-sm">Transaction</a>\n' % aid)
        s.write('<a href="/">Back to accounts list</a></p>\n')

        footer(s)
        return s.getvalue()


    # AJAX handler for reconciliation, toggling a transaction
    # Arguments: 
    #   check99=true        to toggle line 99
    #   stmtbal=9999.99     to set the statement balance
    #   done=1              to finish reconciliation
    @cp.expose
    def reconcileEvent(self, **args):

        # Set statement balance
        if 'stmtbal' in args:
            stmtBal = float(args['stmtbal'])
            cp.session['reconcile_stmt_bal'] = stmtBal
            return '* Statement balance set to %f' % stmtBal

        # Toggle a GL line
        for a in args.keys():
            if a.startswith('clear'):
                lid = int(a[5:])
                on = args[a] == 'true'
                l = GL.get(lid)
                l.cleared = '*' if on else ' '
                return '* GL %d cleared set to %s' % (lid, on)


    # Finish or cancel reconciliation
    @cp.expose
    def finishReconciliation(self, **args):

        # Update flags depending on whether cancelling or not
        cancel = 'cancel' in args
        new_flag = ' ' if cancel else 'X'
        conn = connection.getConnection()
        cur = conn.cursor()
        cur.execute("update GL set cleared = '%s' where cleared = '*'" % new_flag)
        cur.close()
        conn.commit()

        # Turn off reconciliation in session
        if 'reconcile' in cp.session:
            del cp.session['reconcile']
        if 'reconcile_stmt_bal' in cp.session:
            del cp.session['reconcile_stmt_bal']

        # Go back to the account page
        raise cp.HTTPRedirect('/account?id=%d' % cp.session['account'])


    # Page to list all transactions
    @cp.expose
    def transactions(self, **args):

        s = StringIO()
        header(s, 'transactions')
        s.write('<h1>Transactions</h1>\n')

        s.write('<table class="table table-striped table-bordered">\n')
        th(s, ['Date', 'Description', 'Accounts', 'Debit', 'Credit'])
        tdr = tcr = ntrans = 0.0
        for t in Trans.select(orderBy = 'tdate'):

            # Date and description
            ntrans += 1
            s.write('<tr>\n')
            s.write('<td><a href="edit_transaction?tid=%d">%s</a></td>\n' % (t.id, t.tdate))
            s.write('<td>%s</td>\n' % t.description)

            # Account names
            ll = list(t.lines)
            s.write('<td>')
            for l in ll:
                s.write(l.account.name + '<br />')
            s.write('</td>\n')

            # Debits
            s.write('<td style="text-align: right">')
            for l in ll:
                s.write('%s<br />' % ('' if l.debit == 0.0 else '%.2f' % l.debit))
                tdr += l.debit
            s.write('</td>\n')

            # Credits
            s.write('<td style="text-align: right">')
            for l in ll:
                s.write('%s<br />' % ('' if l.credit == 0.0 else '%.2f' % l.credit))
                tcr += l.credit
            s.write('</td>\n')

            s.write('</tr>\n')

        # Totals row
        s.write('<tr style="font-weight: bold">\n')
        s.write('<td colspan="3">Total for %d transactions:</td>\n' % ntrans)
        s.write('<td style="text-align: right">%.2f</td>\n' % tdr)
        s.write('<td style="text-align: right">%.2f</td>\n' % tcr)
        s.write('</tr>\n')


        s.write('</table>\n')
        s.write('<p><a href="/edit_transaction" class="btn btn-primary btn-sm">Add a transaction</a></p>\n')

        footer(s)
        return s.getvalue()


    # Quick way to add a transaction from an account, entering just the offsetting
    # debit/credits, similar to the way Quicken works.
    @cp.expose
    def qtransaction(self, **args):

        # The account to which this transaction applies
        aid = int(args.get('aid',0))
        if not aid:
            return 'Please access this page from within an account'
        qacct = Account.get(aid)

        # The transaction, if editing, otherwise None if creating a new one
        tid = int(args.get('tid', 0))
        if tid:
            qtrans = Trans.get(tid)
        else:
            qtrans = None

        # If editing an existing transaction, get all the lines into a
        # dictionary keyed by line ID
        # line ID => [line ID, account ID, amount]
        lines = {}
        if qtrans :
            for l in qtrans.lines:
                lines[l.id] = [l.id, l.accountID, l.debit, l.credit]

        # Validate the transaction:
        # 1. Must be valid amounts (zero okay to remove a line)
        # 2. Can't have entry to the home account only
        errs = []
        if cp.request.method == 'POST':


            # Get/validate the date and description
            tdate = args['date']
            tdesc = args['descr'].strip()
            if len(tdesc) == 0:
                errs.append('Please enter a description')
            try:
                td = datetime.strptime(tdate, '%d/%m/%Y')
            except:
                errs.append('Invalid date')

            # Collect line info from form, and update the dictionary of lines.
            # Add new lines to the dictionary, these will have negative line
            # IDs.
            for a in args:
                if not '-' in a:
                    continue
                lid = int(a[a.find('-')+1:])
                if not lid in lines:
                    lines[lid] = [lid, 0, 0.0, 0.0]
                if a.startswith('categ'):
                    lines[lid][1] = int(args[a])
                elif a.startswith('debit') or a.startswith('credit'):
                    amt = parse_float(args[a])
                    if amt == None:
                        errs.append('Invalid amount: ' + amt)
                    elif a.startswith('debit'):
                        lines[lid][2] = amt
                    else:
                        lines[lid][3] = amt

            # TODO: Validate

        # Save transaction
        if len(errs) == 0 and cp.request.method == 'POST':

            # Get/create transaction
            if qtrans:
                qtrans.set(tdate = td, description = tdesc)
            else:
                qtrans = Trans(tdate = td, description = tdesc)
                tid = qtrans.id

            # Save date in session
            cp.session['last_date'] = tdate

            # Add/update line for the main account
            totDebits = totCredits = 0.0
            mainLine = None
            for l in lines.values():
                lid, laid, dr, cr = l
                if laid == aid:
                    mainLine = l
                else:
                    totDebits += dr
                    totCredits += cr
            if mainLine:   # Note that we reverse the debits and credits
                mainLine[2] = totCredits
                mainLine[3] = totDebits
            else:
                lines[-99] = [-99, aid, totCredits, totDebits]

            # Save/update/delete individual lines
            for l in lines.values():
                lid, lacctid, dr, cr = l
                if lacctid <= 0 or (dr == 0 and cr == 0):   # no account selected or no amount: ignore or delete line
                    if lid > 0:
                        l = GL.get(lid)
                        l.destroySelf()
                    continue
                lacct = Account.get(lacctid)
                #if lacct.atype in ['A', 'E']: amt *= -1
                if lid > 0:
                    l = GL.get(lid)
                    l.set(trans = tid, account = lacctid, debit = dr, credit = cr)
                else:
                    GL(trans = tid, account = lacctid, debit = dr, credit = cr)

            # Go to page for this account
            raise cp.HTTPRedirect('/account?id=%d' % aid)

        # Start page
        s = StringIO()
        header(s, 'accounts')
        s.write('<h1>%s</h1>\n' % qacct.name)
        for e in errs:
            s.write('<p style="color: red; font-weight: bold">%s</p>\n' % e)

        # Start form, with hidden fields for account and transaction IDs
        s.write('<form action="qtransaction" method="post">\n')
        s.write('<input type="hidden" name="aid" value="%d" />\n' % aid)
        if tid:
            s.write('<input type="hidden" name="tid" value="%d" />\n' % tid)

        # Initialize transaction fields
        if qtrans:
            dt = qtrans.tdate
            descr = qtrans.description
            ds = '%02d/%02d/%d' % (dt.day, dt.month, dt.year)
        elif 'last_date' in cp.session:
            ds = cp.session['last_date']
            descr = ''
        else:
            dt = datetime.today().date()
            ds = '%02d/%02d/%d' % (dt.day, dt.month, dt.year)
            descr = ''

        # Input date and description
        s.write('<p>Date: <input type="text" name="date" value="%s" /></p>\n' % ds)
        s.write('<p>Description:<br/><textarea type="text" name="descr" style="width: 400px; height: 70px">%s</textarea></p>\n' % descr)

        # Labels for debits/credits depend on parent account type
        if qacct.atype == 'A':
            drHint = 'Withdraw'
            crHint = 'Deposit'
        elif qacct.atype == 'L':
            drHint = 'Spend/Borrow'
            crHint = 'Refund/Repay'
        elif qacct.atype == 'E':
            drHint = 'Refund'
            crHint = 'Spend'
        else:   # Income
            drHint = 'Repay'
            crHint = 'Receive'

        # For each line, do a drop-down for category, and input for amount
        ll = list(lines.values()) + [[0, 0, 0, 0]]
        for l in ll:
            lid, laid, ldr, lcr = l
            ldr = '' if ldr == 0 else '%.2f' % ldr
            lcr = '' if lcr == 0 else '%.2f' % lcr
            if laid != aid:   # Don't include home account in list of lines
                s.write('<p><select name="categ-%d">\n' % lid)
                s.write('  <option value="0">-- category --</option>\n')
                for a in Account.select(orderBy = 'name'):
                    if a.id != aid:  # do not include the home account in the dropdown list
                        sel = 'selected="selected"' if a.id == laid else ''
                        s.write('  <option value="%d" %s>%s</option>\n' % (a.id, sel, a.name))
                s.write('</select>\n')
                s.write('<input type="text" name="debit-%d" value="%s" placeholder="%s">\n' % (lid, ldr, drHint))
                s.write('<input type="text" name="credit-%d" value="%s" placeholder="%s"></p>\n' % (lid, lcr, crHint))
        s.write('<p><input type="submit" class="btn btn-primary btn-sm" value="Save" /></p>\n')
        s.write('</form>\n')

        # Show transaction below, for debugging
        if qtrans:
            s.write('<hr/>\n')
            s.write('<table>\n<tr>\n')
            for h in ['Account', 'Debit', 'Credit']:
                s.write('  <th>%s</th>\n' % h)
            s.write('</tr>\n')
            for l in qtrans.lines:
                s.write('<tr>\n')
                s.write('  <td>%s (%s)</td>\n' % (l.account.name, l.account.atype))
                s.write('  <td style="text-align: right">%.2f</td>\n' % l.debit)
                s.write('  <td style="text-align: right">%.2f</td>\n' % l.credit)
                s.write('</tr>\n')
            s.write('</table>\n')

        # Finish page
        footer(s)
        return s.getvalue()

    
    # Reports menu
    @cp.expose
    def reports(self, **args):

        s = StringIO()
        header(s, 'reports')
        s.write('<h1>Reports</h1>\n')

        s.write('<ul>\n')
        for r in ['balance_sheet', 'income_statement']:
            s.write('<li><a href="/%s">%s</a></li>\n' % (r, r.replace('_', ' ').title()))
        s.write('</ul>\n')

        footer(s)
        return s.getvalue()


    # Balance sheet
    @cp.expose
    def balance_sheet(self, **args):

        s = StringIO()
        header(s, 'reports')
        s.write('<h1>Balance Sheet</h1>\n')
        s.write('<table style="width: 100%">\n')

        # Assets
        accounts =  list(Account.select(orderBy = 'number'))
        s.write('<tr><td colspan="2" style="font-weight: bold">ASSETS</td></tr>\n')
        totAss = 0.0
        for a in accounts:
            if a.atype != 'A':
                continue
            bal = a.getBalance()
            s.write('<tr><td><a href="/account?id=%d" style="width: 200px">%s</a></td>' % (a.id, a.name))
            s.write('<td style="text-align: right">%.2f</td></tr>\n' % bal)
            totAss += bal
        s.write('<tr><td>Total assets:</td><td style="text-align: right; border-top: 1px solid black">%.2f</td></tr>\n' % totAss)

        # Liabilities
        s.write('<tr><td colspan="3">&nbsp;</td></tr>\n')
        s.write('<tr><td colspan="2" style="font-weight: bold">LIABILITIES</td></tr>\n')
        totLiab = 0.0
        for a in accounts:
            if a.atype != 'L':
                continue
            bal = a.getBalance() * -1.0
            s.write('<tr><td><a href="/account?id=%d" style="width: 200px">%s</a></td>' % (a.id, a.name))
            s.write('<td style="text-align: right">%.2f</td></tr>\n' % bal)
            totLiab += bal
        s.write('<tr><td>Total liabilities:</td><td style="text-align: right; border-top: 1px solid black">%.2f</td></tr>\n' % totLiab)

        # Shareholders' Equity (just a plug for now)
        s.write('<tr><td colspan="3">&nbsp;</td></tr>\n')
        s.write('<tr><td colspan="2" style="font-weight: bold">SHAREHOLDERS\' EQUITY</td></tr>\n')
        totEquity = totAss - totLiab 
        s.write('<tr><td>Total Equity:</td><td style="text-align: right; border-top: 1px solid black">%.2f</td></tr>\n' % totEquity)

        # Total liabilities and equity
        #s.write('<tr><td colspan="3">&nbsp;</td></tr>\n')
        #s.write('<tr><td>TOTAL LIABILITIES AND EQUITY</td><td style="text-align: right; border-top: 1px solid black">%.2f</td></tr>\n' % (totLiab + totEquity))

        s.write('</table>\n')
        footer(s)
        return s.getvalue()


    # Income statement
    @cp.expose
    def income_statement(self, **args):

        s = StringIO()
        header(s, 'reports')
        s.write('<h1>Income Statement</h1>\n')
        s.write('<table style="width: 100%">\n')

        # Income
        s.write('<tr><td colspan="2" style="font-weight: bold">INCOME</td></tr>\n')
        totInc = 0.0
        for a in Account.select('atype == "I"', orderBy = 'number'):
            bal = a.getBalance()
            s.write('<tr><td><a href="/account?id=%d" style="width: 200px">%s</a></td>' % (a.id, a.name))
            s.write('<td style="text-align: right">%.2f</td></tr>\n' % bal)
            totInc += bal
        s.write('<tr><td>Total income:</td><td style="text-align: right; border-top: 1px solid black">%.2f</td></tr>\n' % totInc)

        # Expenses
        s.write('<tr><td colspan="3">&nbsp;</td></tr>\n')
        s.write('<tr><td colspan="2" style="font-weight: bold">EXPENSES</td></tr>\n')
        totExp = 0.0
        for a in Account.select('atype == "E"', orderBy = 'number'):
            bal = a.getBalance()
            s.write('<tr><td><a href="/account?id=%d" style="width: 200px">%s</a></td>' % (a.id, a.name))
            s.write('<td style="text-align: right">%.2f</td></tr>\n' % bal)
            totExp += bal
        s.write('<tr><td>Total expenses:</td><td style="text-align: right; border-top: 1px solid black">%.2f</td></tr>\n' % totExp)

        # Net income
        s.write('<tr><td colspan="3">&nbsp;</td></tr>\n')
        s.write('<tr><td colspan="2" style="font-weight: bold">NET INCOME</td></tr>\n')
        netInc = totInc - totExp 
        s.write('<tr><td>Net Income:</td><td style="text-align: right; border-top: 1px solid black">%.2f</td></tr>\n' % netInc)

        s.write('</table>\n')
        footer(s)
        return s.getvalue()



# Start a new page
def header(s, current):

    # Basic header stuff
    s.write(open('static/header.html').read())
    if not current:
        return

    # Navigation bar
    s.write('<nav class="navbar navbar-default">\n')
    s.write('<div class="container-fluid">\n')

    # Navbar header (just site name for now)
    s.write('<div class="navbar-header">\n')
    s.write('  <a class="navbar-brand" href="/accounts">Accountz.online</a>\n')
    s.write('</div>\n')

    # Menu links
    menu = ['accounts', 'transactions', 'reports']
    s.write('<ul class="nav navbar-nav">\n')
    for m in menu:
        #c = 'class="active"' if m == current else ''  #BOOTSTRAP ACTIVE CLASS NOT WORKING
        c = 'style="background-color: #eee"' if m == current else ''
        s.write('<li %s><a href="/%s">%s</a></li>\n' % (c, m, m.title()))
    s.write('</ul>\n')

    # End of navigation bar
    s.write('</nav>\n')   # end of navigation bar

    # Content div
    s.write('<div class="container">\n')


# Finish page
def footer(s):
    s.write(open('static/footer.html').read())


# Table header row
def th(s, headings):
    s.write('<tr>\n')
    for h in headings:
        s.write(' <th>%s</th>\n' % h)
    s.write('</tr>\n')


# Parse a float, return None if invalid
def parse_float(s, blank_value = None):
    if s.strip() == '':
        return blank_value
    try:
        return float(s)
    except Exception, e:
        return None


# Parse a "dd/mm/yyyy" date, return datetime.date or None
def parse_date(s):
    try:
        d, m, y = [int(x) for x in s.split('/')]
        return date(y,m,d)
    except Exception, e:
        return None


# Format a date as "dd/mm/yyyy"
def format_date(d):
    return '%02d/%02d/%d' % (d.day, d.month, d.year) 


# WHY IS THERE A SECOND VERSION OF THIS (SEE ABOVE)?
def parse_float(n):
    n = n.strip()
    if len(n) == 0:
        return 0.0
    try:
        return float(n)
    except:
        return None


def workstation():
    return socket.gethostname() in ['shuttle', 'zenbook']


# Global settings
globalSettings = { 'server.socket_port' : 8003 }
globalSettings['log.screen'] = workstation()
#globalSettings['request.error_response'] = errorHandler
globalSettings['log.error_file'] = '/tmp/accountz.err'
globalSettings['access_log.filename'] = '/tmp/accountz.log'

# Different settings for workstation vs. production
if workstation():
    globalSettings['server.thread_pool'] = 1
else:
    globalSettings['environment'] = 'production'
    globalSettings['server.thread_pool'] = 3

# Application settings
# Warning: staticdir, is very slow, run behind lighttpd if possible
appSettings = {}
appSettings['/'] = {
    'tools.sessions.on'             : True,
    'tools.sessions.storage_type'   : 'File',
    'tools.sessions.storage_path'   : '/tmp',
    'tools.sessions.timeout'   : 90, #, 'error_page.404' : 'static/404.html' 
    'tools.staticdir.root' : os.getcwd()
}
appSettings['/static'] = {
    'tools.staticdir.on' : True,
    'tools.staticdir.dir' : 'static'
}

# Start server
cp.config.update(globalSettings)
cp.quickstart(Main(), config = appSettings)

