"""
<Program Name>
  depdata.py

<Purpose>
  This module houses the globals to be used by deptools, resolver, scraper.
  
  TODO: Move the data descriptions into this docstring.

"""

dependencies_by_dist = None
conflicts_db = None  # ALIAS to conflict db in use. For convenience/legacy. /:
conflicts_1_db = None
conflicts_2_db = None
conflicts_3_db = None
#conflict_model = None # Not currently used.

# Shouldn't REALLY be in here, since only scrape uses this, but it's tidier
# to keep it all together and it's not much overhead.
blacklist = None

import os
import json

# Filenames
WORKING_DIRECTORY = os.path.join(os.getcwd()) #'/Users/s/w/git/pypi-depresolve' in my setup
DEPENDENCY_CONFLICTS1_DB_FILENAME = os.path.join(WORKING_DIRECTORY, 'data',
    'conflicts_1.json') # db for model 1 conflicts
DEPENDENCY_CONFLICTS2_DB_FILENAME = os.path.join(WORKING_DIRECTORY, 'data',
    'conflicts_2.json') # db for model 2 conflicts
DEPENDENCY_CONFLICTS3_DB_FILENAME = os.path.join(WORKING_DIRECTORY, 'data',
    'conflicts_3.json') # db for model 3 conflicts
BLACKLIST_DB_FILENAME = os.path.join(WORKING_DIRECTORY, 'data', 
    'blacklist.json')
DEPENDENCIES_DB_FILENAME = os.path.join(WORKING_DIRECTORY, 'data',
    'dependencies.json')





def load_json_db(fname):
  """
  Load given filename as a json file. If it's invalid or doesn't exist, load an
  empty dict and create the file anew. Give the user a chance to control-c if
  file contents are invalid or file doesn't exist, by prompting for enter.
  """
  # Fill with JSON data from file.
  db = None

  assert(os.path.exists(WORKING_DIRECTORY))

  # Python 2/3 compatibility.
  try:
    input_ = raw_input # if python 2, override input to be raw_input
  except NameError:  # if python 3, there's no raw_input - but then we're OK
    input_ = input


  if not os.path.exists(fname):
    print('  Directed to load ' + fname + ' but file does not exist. Will '
        'CREATE A NEW FILE AND LOAD AN EMPTY DICTIONARY. ')

    input('  PRESS ENTER TO CONTINUE, CONTROL-C TO KILL AND MANUALLY HANDLE.')

    dirname = os.path.dirname(fname)
    if not os.path.exists(dirname):
      print("Directory check: " + dirname + " does not exist. Making it.")
      os.makedirs(dirname)

    open(fname, 'a').close()
    db = dict()

  else: # File exists
    fobj = None

    try:
      fobj = open(fname, "r")
      db = json.load(fobj)

    except IOError:
      print('  Directed to load " + filename + " but UNABLE TO OPEN file. '
          'Crashing.')
      raise

    except ValueError:
      print('  Directed to load ' + fname + '; able to open file, but '
          'UNABLE TO PARSE JSON DATA from that file. Will load an empty dict '
          'and ultimately EXPECT TO OVERWRITE UNREADABLE JSON.')
      input('  PRESS ENTER TO CONTINUE, CONTROL-C TO KILL AND AVOID '
          'POTENTIALLY OVERWRITING SALVAGEABLE DATA.')
      db = dict() # If it was invalid or the file didn't exist, load empty.

    finally:
      try:
        fobj.close()
      except:
        pass


  return db





def ensure_data_loaded(CONFLICT_MODELS=[1, 2, 3]):
  """
  Ensure that the global dependencies, conflicts, and blacklist dictionaries
  are loaded, importing them now if not.

  If the global is not defined yet, load the contents of the json file.

  Use load_json_db() to ensure that user has an opportunity to cancel each of
  these:
    - If the db file doesn't exist, create it (open in append mode and close)
    - If the json parse fails, create a fresh dictionary.

  """
  global dependencies_by_dist
  global conflicts_1_db
  global conflicts_2_db
  global conflicts_3_db
  global blacklist



  if dependencies_by_dist is None:
    dependencies_by_dist = load_json_db(DEPENDENCIES_DB_FILENAME)

  if conflicts_1_db is None and 1 in CONFLICT_MODELS:
    conflicts_1_db = load_json_db(DEPENDENCY_CONFLICTS1_DB_FILENAME)

  if conflicts_2_db is None and 2 in CONFLICT_MODELS:
    conflicts_2_db = load_json_db(DEPENDENCY_CONFLICTS2_DB_FILENAME)

  if conflicts_3_db is None and 3 in CONFLICT_MODELS:
    conflicts_3_db = load_json_db(DEPENDENCY_CONFLICTS3_DB_FILENAME)

  if blacklist is None:
    blacklist = load_json_db(BLACKLIST_DB_FILENAME)


  # Trivial validation. (Should do better - TODO.)
  assert type(dependencies_by_dist) is dict

  if 1 in CONFLICT_MODELS:
    assert type(conflicts_1_db) is dict
  if 2 in CONFLICT_MODELS:
    assert type(conflicts_2_db) is dict
  if 3 in CONFLICT_MODELS:
    assert type(conflicts_3_db) is dict

  assert type(blacklist) is dict

  print('depresolve globals have been imported.')





def set_conflict_model_legacy(CONFLICT_MODEL):
  """
  For my convenience, sticks a reference to the active conflict model's
  dict in alias "conflict_db"
  """
  global conflicts_db
  global conflicts_1_db
  global conflicts_2_db
  global conflicts_3_db

  if CONFLICT_MODEL == 1:
    conflicts_db = conflicts_1_db

  elif CONFLICT_MODEL == 2:
    conflicts_db = conflicts_2_db

  elif CONFLICT_MODEL == 3:
    conflicts_db = conflicts_3_db

  else:
    assert False, "Programming error. Invalid conflict model."





def write_data_to_files(CONFLICT_MODELS=[1, 2, 3]):
  """"""
  global dependencies_by_dist
  global conflicts_1_db
  global conflicts_2_db
  global conflicts_3_db
  global blacklist

  json.dump(dependencies_by_dist, open(DEPENDENCIES_DB_FILENAME, 'w'))
  json.dump(blacklist, open(BLACKLIST_DB_FILENAME, 'w'))

  if 1 in CONFLICT_MODELS:
    json.dump(conflicts_1_db, open(DEPENDENCY_CONFLICTS1_DB_FILENAME, 'w'))

  if 2 in CONFLICT_MODELS:
    json.dump(conflicts_2_db, open(DEPENDENCY_CONFLICTS2_DB_FILENAME, 'w'))

  if 3 in CONFLICT_MODELS:
    json.dump(conflicts_3_db, open(DEPENDENCY_CONFLICTS3_DB_FILENAME, 'w'))



# def get_conflicts_db_fname(CONFLICT_MODEL):
#   """
#   Maps conflict model to conflicts db filename.
#   """
#   conflicts_db_filename = None

#   if CONFLICT_MODEL == 1:
#     conflicts_db_filename = DEPENDENCY_CONFLICTS1_DB_FILENAME
#   elif CONFLICT_MODEL == 2:
#     conflicts_db_filename = DEPENDENCY_CONFLICTS2_DB_FILENAME
#   elif CONFLICT_MODEL == 3:
#     conflicts_db_filename = DEPENDENCY_CONFLICTS3_DB_FILENAME
#   else:
#     assert False, "Programming error. Invalid conflict model " + \
#     str(CONFLICT_MODEL)

#   return conflicts_db_filename




def deps_are_equal(deps_a, deps_b):
  """
  Returns true if given lists of dependencies that are equivalent
  (regardless of order).
  
  Update: This is now QUITE A BIT simpler. It may not really be necessary
  anymore. I stripped all the ugliness and replaced it with this line (which
  didn't work before for unpleasant Reasons explained in comments in previous
  versions).
  """
  return sorted(deps_a) == sorted(deps_b)





# General purpose utility functions.
def get_pack_and_version(distkey):
  """
  Convert a distkey, e.g. 'django(1.8.3)', into a package name and
  version string, e.g. ('django', '1.8.3').

  Reverse: distkey_format()
  """
  packagename = get_packname(distkey)
  version = get_version(distkey)
  return (packagename, version)





def get_packname(distkey):
  """The package name ends with the first open parenthesis."""
  return distkey[:distkey.find('(')]





def get_version(distkey):
  """
  Note that the version string may contain parentheses. /:
  So it's just every character after the first '(' until the last
  character, which must be ')'.
  """
  return distkey[distkey.find('(') + 1 : -1]





def distkey_format(package_name, version_string):
  """
  Combine a package name and version string (e.g. 'django', '1.8.3') into a
  distkey e.g. 'django(1.8.3)'

  Reverse: get_pack_and_version()
  """
  return package_name + '(' + version_string + ')'





def get_distkey_from_dist(dist):
  """
  Determines the key for a given distribution to be
  used in the dependency conflict db and the dependencies db.
  Splitting into two calls to allow for use on either a dist object or
  just name and version strings.

  Note that the argument dist here is an object of an internal pip type.
  (Gotta dig the class back up later.)

  It doesn't make a TON of sense for this to be here, since this module need
  not know anything about the dist type (which is a pip internal), but I wasn't
  sure where else it was worth putting, save in pip.req.req_set itself....

  """
  return distkey_format(dist.project_name, dist.version)


