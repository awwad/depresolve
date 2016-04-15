"""
<Program Name>
  sql_i.py

<Purpose>
  This module provides sqlite3 interface and data for deptools and the
  resolver.

  Not thread-safe :D
  
"""

import depresolve # __init__ for logging
import sqlite3 # dependency db as sqlite db is the future of this :P


SQL_CONNECTION = None
SQL_CURSOR = None

sql_dependency_fname = 'dependency.db'

SQL_DEPENDENCY_TABLE = 'elaborated_dependencies'
SQL_DEP_SPECIFIER_TABLE = 'dependency_specifiers'
SQL_NO_DEPS_TABLE = 'dists_with_no_dependencies'
SQL_NO_VERS_INFO_TABLE = 'packages_without_version_info'
SQL_MISSING_DEPS_TABLE = 'missing_dependencies'

SQL_COLUMN_DEPENDER_DIST_KEY = 'depender_dist_key'
SQL_COLUMN_SATISFYING_PACK_NAME = 'satisfying_pack_name'
SQL_COLUMN_SATISFYING_DIST_KEY = 'satisfying_dist_key'
SQL_COLUMN_SATISFYING_SPECIFIER = 'satisfying_specifier'
SQL_COLUMN_PACK_NAME = 'pack_name'


SQL_DEPENDENCY_TBLDEF = (
    "CREATE TABLE IF NOT EXISTS " + SQL_DEPENDENCY_TABLE + "(" +
        SQL_COLUMN_DEPENDER_DIST_KEY + " TEXT, " +
        SQL_COLUMN_SATISFYING_PACK_NAME + " TEXT, " +
        SQL_COLUMN_SATISFYING_DIST_KEY + " TEXT, "
        "PRIMARY KEY(" +
            SQL_COLUMN_DEPENDER_DIST_KEY + ", " + 
            SQL_COLUMN_SATISFYING_DIST_KEY +
        ") ON CONFLICT REPLACE" +
    ")")

SQL_DEP_SPECIFIER_TBLDEF = (
    "CREATE TABLE IF NOT EXISTS " + SQL_DEP_SPECIFIER_TABLE + "(" +
        SQL_COLUMN_DEPENDER_DIST_KEY + " TEXT, " +
        SQL_COLUMN_SATISFYING_PACK_NAME + " TEXT, " +
        SQL_COLUMN_SATISFYING_SPECIFIER + " TEXT, " +
        "PRIMARY KEY(" +
            SQL_COLUMN_DEPENDER_DIST_KEY + ", " +
            SQL_COLUMN_SATISFYING_PACK_NAME +
        ") ON CONFLICT REPLACE" +
    ")")

SQL_NO_DEPS_TBLDEF = (
    "CREATE TABLE IF NOT EXISTS " + SQL_NO_DEPS_TABLE + "(" +
        SQL_COLUMN_DEPENDER_DIST_KEY + " TEXT, " +
        "PRIMARY KEY(" + SQL_COLUMN_DEPENDER_DIST_KEY +
        ") ON CONFLICT REPLACE" +
    ")")
  
SQL_NO_VERS_INFO_TBLDEF = (
    "CREATE TABLE IF NOT EXISTS " + SQL_NO_VERS_INFO_TABLE +
    "(" +
        SQL_COLUMN_PACK_NAME + " TEXT, " +
        "PRIMARY KEY(" + SQL_COLUMN_PACK_NAME +
        ") ON CONFLICT REPLACE" +
    ")")

SQL_MISSING_DEPS_TBLDEF = (
    "CREATE TABLE IF NOT EXISTS " + SQL_MISSING_DEPS_TABLE + "(" +
        SQL_COLUMN_DEPENDER_DIST_KEY + " TEXT, " +
        SQL_COLUMN_SATISFYING_PACK_NAME + " TEXT, " +
        "PRIMARY KEY(" +
            SQL_COLUMN_DEPENDER_DIST_KEY + ', ' +
            SQL_COLUMN_SATISFYING_PACK_NAME +
        ") ON CONFLICT REPLACE" +
    ")")




# SQLITE3 interfacing functions
def initialize(db_fname=None):
  """
  Initializes the connection to the database and saves the connection and
  cursor to module globals. Also initializes the database itself if it is not
  initialized. That is, creates the sqlite3 tables necessary for the dependency
  database, an enumerated dependencies table and a dependency specifiers table.
  
  In the schemas defined above, the create instruction reads "CREATE TABLE IF
  NOT EXISTS", so they will simply ensure that the given tables exist: If they
  are not defined, they will be created. If they are already defined, they will
  not be modified.

  If db_fname is provided, this module will be configured to use that filename
  for the database file with all future actions, otherwise it will use the
  module's default value for sql_dependency_fname.

  """

  if db_fname is not None:
    global sql_dependency_fname
    sql_dependency_fname = db_fname

  global SQL_CONNECTION
  global SQL_CURSOR
  SQL_CONNECTION = sqlite3.connect(sql_dependency_fname)
  SQL_CURSOR = SQL_CONNECTION.cursor()

  all_tabledefs = [
      SQL_DEPENDENCY_TBLDEF,
      SQL_DEP_SPECIFIER_TBLDEF,
      SQL_NO_DEPS_TBLDEF,
      SQL_NO_VERS_INFO_TBLDEF,
      SQL_MISSING_DEPS_TBLDEF]

  for tabledef in all_tabledefs:
    print("Creating table " + tabledef)
    SQL_CURSOR.execute(tabledef)


def add_to_table(
    tablename,
    depender_dist_key,
    satisfying_pack_name,
    third_argument): # Can be satisfying_dist_key or satisfying_specifier
  """
  Given a dependency specifier or dependency, add it to the indicated table:
  dependencies or dependency specifiers.

  TODO: Rewrite slightly to use **kwargs for arbitrary column names, and
  validate.
  """
  logger = resolver.logging.getLogger('add_to_table')
  _ensure_connected_to_sqlite()

  global SQL_CURSOR

  logger.info("           SQLI: \n"
      "INSERT INTO " + tablename + " VALUES (" + depender_dist_key + ", " +
      satisfying_pack_name + ", " + third_argument + ")")

  SQL_CURSOR.execute("INSERT INTO " + tablename + " VALUES (?, ?, ?)",
      (
          depender_dist_key,
          satisfying_pack_name,
          third_argument
      )
  )

def flush():
  """
  """
  global SQL_CURSOR
  global SQL_CONNECTION
  SQL_CONNECTION.commit()




def delete_all_tables():
  """ Clear the db. """
  _ensure_connected_to_sqlite()
  global SQL_CURSOR
  
  all_tables = [
      SQL_DEPENDENCY_TABLE,
      SQL_DEP_SPECIFIER_TABLE,
      SQL_NO_DEPS_TABLE,
      SQL_NO_VERS_INFO_TABLE,
      SQL_MISSING_DEPS_TABLE]

  for tablename in all_tables:
    SQL_CURSOR.execute('drop table ' + tablename)
  
  flush()




def _ensure_connected_to_sqlite():
  """
  Ensures that the SQL_CONNECTION and SQL_CURSOR module variables are
  defined. If there isn't an existing connection and cursor, connect and
  create a cursor.
  """
  global SQL_CONNECTION
  global SQL_CURSOR

  if SQL_CONNECTION is None:
    SQL_CONNECTION = sqlite3.connect(sql_dependency_fname)
    assert SQL_CURSOR is None, "Programming error."
  if SQL_CURSOR is None:
    SQL_CURSOR = SQL_CONNECTION.cursor()
  
