"""
<Program Name>
  depdata.py

<Purpose>
  This module houses the globals to be used by deptools, resolver, scraper.

  I've made sample data - already crunched in the formats below for all PyPI
  packages current to late 2015 - available at:
    https://www.dropbox.com/sh/2x870eosiknww68/AAArQBivh2jlu6auqNLHsm1Ja?dl=0

  You can pull it from dropbox at the link provided or download all of it
  (52MB zipped) via shell like so:
    > curl -L -o dep_data.zip https://www.dropbox.com/sh/2x870eosiknww68/AAArQBivh2jlu6auqNLHsm1Ja?dl=1
    > unzip dep_data.zip


<Data Specification>

 distkey (distribution key):

    A distkey is the unique identifier we use for a distribution, being a
    particular concatenation of the package name and version string, separated
    by parentheses.

    Examples:
      django(1.8.3)   version 1.8.3 of package 'django'
      foo(1.0b3)      version 1.0b3 (1.0 beta 3) of package 'foo'

    We expect version strings to be compatible with the Version or
    LegacyVersion classes defined in pip._vendor.packaging.version. In
    practice, anything that works for pip should work for us. Given a string
    version_string, pip._vendor.packaging.version.parse(version_string) should
    not raise pip._vendor.packaging.version.InvalidVersion.

    Package names are less rigorously constrained, but should ideally be all
    lowercase, and employ '-' rather than '_'. Again, what works in pip should
    work here.
    (TODO: Point to pip's specification.)

 

 dep (dependency):

    A dependency takes the form of the two-member list, the first member being
    the name of the package depended on, and the second member being a
    requirement or specifier string. Such strings should match the
    specifications of pip._vendor.packaging.version.Specifier. The format is
    also documented here:
      https://pip.pypa.io/en/stable/reference/pip_install/#requirement-specifiers

    In practice, feeding string x to
    pip._vendor.packaging.version.SpecifierSet(x) should not result in an
    error. Generally, if pip understands a specifier string, so should we.

    examples:
      ['pymongo', '==2.5']           # a dependency on pymongo version 2.5
      ['six', '']                    # dependency on any version of six
      ['foo', '<5.0.1']              # dep on any ver of foo under 5.0.1
      ['bar', '>=6.0,!=6.2.1,<8.0']  # ver >= 6, less than 8, and not 6.2.1



 deps (dependencies dictionary):

    This is often 'deps' or 'dependencies_by_dist' in the code.

    The data format we use for dependency info, which I'll generally refer to
    as 'deps', is a dictionary with keys being distkeys (e.g. 'django(1.8.3)').
    The value associated with each distkey in the dictionary is a list of
    individual dependencies, each dependency being the length-two list 'dep'
    format above.

       e.g., here is a deps dictionary:

         {'motorengine(0.7.4)':           # distribution motorengine 0.7.4
            [  ['pymongo', '==2.5'],      # depends on pymongo version 2.5
               ['tornado', ''],           # and any version of tornado
               ['motor', ''],             # and any version of motor
               ['six', ''],               # and any version of six
               ['easydict', '']           # and any version of easydict
            ],
          'django(1.8.3)':                # version 1.8.3 of package django
            [],                           # has no dependencies
          'django(1.6.3)':
            [],
          'django(1.7)':
            [],
          'chembl-webservices(2.2.11)':
            [  ['lxml', ''],
               ['pyyaml', '>=3.10'],
               ['defusedxml', '>=0.4.1'],
               ['simplejson', '==2.3.2'],
               ['pillow', '>=2.1.0'],
               ['django-tastypie', '==0.10'],
               ['chembl-core-model', '>=0.6.2'],
               ['cairocffi', '>=0.5.1'],
               ['numpy', '>=1.7.1'],
               ['mimeparse', ''],
               ['raven', '>=3.5.0],
               ['chembl-beaker', '>=0.5.34']
            ],
          ...
          ...
         }



 edep (elaborated dependency):

    An elaborated dependency is a three-member list, essentially just deps
    with an additional member between the two original members: the list of
    available versions satisfying the dependency.

    Example:
      [
        'foo',                          # str: depended-on package
        ['1.0', '1.1', '1.2', '1.2.5'], # list: all satisfying versions
        '>=1,<1.3'                      # str: the specifier/requirement string
      ]

    The additional list identifies a list of every specific version of a
    depended-on package that would satisfy the depending package's dependency
    on the depended-on package. (Mouthful!)

    The specifier string is redundant but provided for convenience.



 edeps (elaborated dependencies dictionary):

    The similarly augmented version of deps.

    Example:
     {
      'django(1.7)': [],       # django 1.7 has no dependencies

      'foo(1)': [                        # version 1 of foo
        'bar',                           # depends on package bar,
        ['1.0', '1.1', '3', '4.2.5b4'],  # any of these available versions
        ''                               # specifier was any version
      ],

      'X(1.0)': [                 # distribution X-1.0
        ['B', ['2.5'], '==2.5'],  # depends on package B, version 2.5,
                                  # which exists
        
        ['C', ['1', '2'], ''],  # and version 1 or 2 of package C
                                # those being the only available versions of C

        ['D', ['1.9', '1.10'], '>=1.9,<1.10.3'] # and versions 1.9 or 1.10 of
                                                # package D, as those are the
                                                # only available versions that
                                                # fit '>=1.9,<1.10.3'.
      ]
     }

 conflicts_db (dictionary of conflicting distributions)



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
WORKING_DIRECTORY = os.path.join(os.getcwd()) #'/Users/s/w/git/depresolve' in my setup
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
  dict in alias "conflict_db". The dependence on such an alias makes me a bit
  nervous, so we should move away from it by updating scraper code. /:
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


