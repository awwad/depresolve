# Subpackage of the resolver for sqlite interaction.

# I am not thread-safe. :D

import sqlite3 # dependency db as sqlite db is the future of this :P

import logging

SQL_CONNECTION = None
SQL_CURSOR = None
sql_dependency_fname = 'dependency.db'
SQL_DEPENDENCY_TABLENAME = 'dependencies'
SQL_DEP_SPECIFIER_TABLENAME = 'dependency_specifiers'
SQL_COLUMN_DEPENDER_DIST_KEY = 'depender_dist_key'
SQL_COLUMN_SATISFYING_PACK_NAME = 'satisfying_pack_name'
SQL_COLUMN_SATISFYING_DIST_KEY = 'satisfying_dist_key'
SQL_COLUMN_SATISFYING_SPECIFIER = 'satisfying_specifier'
SQL_DEPENDENCY_SCHEMA = (
    "CREATE TABLE IF NOT EXISTS " + SQL_DEPENDENCY_TABLENAME +
    "(" +
        SQL_COLUMN_DEPENDER_DIST_KEY + " TEXT, " +
        SQL_COLUMN_SATISFYING_PACK_NAME + " TEXT, " +
        SQL_COLUMN_SATISFYING_DIST_KEY + " TEXT, "
        "PRIMARY KEY" +
        "(" +
            SQL_COLUMN_DEPENDER_DIST_KEY + ", " + 
            SQL_COLUMN_SATISFYING_DIST_KEY +
        ") ON CONFLICT REPLACE" +
    ")"
    )
SQL_DEP_SPECIFIER_SCHEMA = (
    "CREATE TABLE IF NOT EXISTS " + SQL_DEP_SPECIFIER_TABLENAME +
    "(" +
        SQL_COLUMN_DEPENDER_DIST_KEY + " TEXT, " +
        SQL_COLUMN_SATISFYING_PACK_NAME + " TEXT, " +
        SQL_COLUMN_SATISFYING_SPECIFIER + " TEXT, " +
        "PRIMARY KEY" +
        "(" +
            SQL_COLUMN_DEPENDER_DIST_KEY + ", " +
            SQL_COLUMN_SATISFYING_PACK_NAME +
        ") ON CONFLICT REPLACE" +
    ")"
    )



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

  SQL_CURSOR.execute(SQL_DEPENDENCY_SCHEMA)
  SQL_CURSOR.execute(SQL_DEP_SPECIFIER_SCHEMA)

def add_to_table(
    tablename,
    depender_dist_key,
    satisfying_pack_name,
    third_argument): # Can be satisfying_dist_key or satisfying_specifier
  """
  Given a dependency specifier or dependency, add it to the indicated table,
  dependencies or dependency specifiers.

  TODO: Rewrite slightly to use **kwargs for arbitrary column names.
  """
  logger = logging.getLogger('add_to_table')
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
  _ensure_connected_to_sqlite()
  global SQL_CURSOR
  SQL_CURSOR.execute('drop table dependencies')
  SQL_CURSOR.execute('drop table dependency_specifiers')
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
  
