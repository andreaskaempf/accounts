# Accounts
This is a simple browser-based double-entry accounting system written in Python, inspired by Quicken. It allows you to create accounts, enter transactions, and view income statement, net worth (balance sheet) and other reports.

To run it, you need to install to install sqlobject and cherrypy:

pip install sqlobject
pip install cherrypy

It uses SQLite as the database, but this can be easily changed to PostgreSQL or another relational database that has a Python DBAPI connector, see the commented-out connect string at the top of db.py and the SQLObject documentation.

It is currently in Python 2, but should be easy to migrate to Python 3.

You also need to install bootstrap3 in the static directory; this will be changed to bootstrap4 in due course.

If you are using it for the first time, type "./db.py create" to create a new database with the required tables.

Andreas Kaempf
Neubiberg, Germany
Project started 18/12/2013

