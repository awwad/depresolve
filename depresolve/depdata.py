"""
<Program Name>
  depdata.py

<Purpose>
  This module houses the globals to be used by resolvers and the scraper.
  Data is harvested by the scraper (scrape_deps_and_detect_conflicts) into
  formats described here.

  This module also contains a variety of functions for dealing with that data.

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

    Package names are less rigorously constrained, but should be all lowercase
    and employ '-' rather than '_'. Again, what works in pip should work here,
    except for casing, where we are stricter (all lowercase for package names
    and version numbers.

    I'm also less thorough about not accepting special characters in distkeys
    than pip likely is.

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

    A dictionary mapping distkey to boolean indicating whether or not a
    dependency conflict exists for that distribution.

    Stored as conflicts_1.json, conflicts_2.json, conflicts_3.json,
    respectively for the associated conflict models (1, 2, or 3), defined in
    README.md and docs/background.md.

    Example:
      {
        'motorengine(0.7.2)': True,
        'django(1.7.1)': False,
        'foo(1)': False
      }



  List of functions provided in this module:

    load_json_db
    ensure_data_loaded
    set_conflict_model_legacy
    old_normalize_version_string
    write_data_to_files
    deps_are_equal
    get_pack_and_version
    get_packname
    get_version
    distkey_format
    is_valid_distkey
    get_distkey_from_dist
    versions_are_equal
    fix_deps_case
    assume_dep_data_exists_for
    is_dep_valid
    are_deps_valid
    normalize_distkey
    normalize_package_name
    normalize_version_string
    old_normalize_version_string
    spectuples_to_specset
    spectuples_to_specstring
    elaborate_dependencies
    _elaborate_dependency

"""

#from depresolve import MissingDependencyInfoError
import depresolve # for errors and logging
import pip._vendor.packaging.version # for version validation

dependencies_by_dist = None
versions_by_package = None
elaborated_dependencies = None
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
ELAORATED_DEPS_FILENAME = os.path.join(WORKING_DIRECTORY, 'data',
    'elaborated_dependencies.json')


# Constants
PACKAGE_VERSIONS_UNKNOWN = ['----ERROR--UNAVAILABLE-VERSION-INFORMATION----']




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

    input_('  PRESS ENTER TO CONTINUE, CONTROL-C TO KILL AND MANUALLY HANDLE.')

    dirname = os.path.dirname(os.path.abspath(fname))
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
      input_('  PRESS ENTER TO CONTINUE, CONTROL-C TO KILL AND AVOID '
          'POTENTIALLY OVERWRITING SALVAGEABLE DATA.')
      db = dict() # If it was invalid or the file didn't exist, load empty.

    finally:
      try:
        fobj.close()
      except:
        pass


  return db





def ensure_data_loaded(CONFLICT_MODELS=[1, 2, 3], include_edeps=False):
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
  global versions_by_package # not KEPT in sync with dependencies_by_dist
  global elaborated_dependencies # not KEPT in sync with dependencies_by_dist
  global conflicts_1_db
  global conflicts_2_db
  global conflicts_3_db
  global blacklist



  if dependencies_by_dist is None:
    dependencies_by_dist = load_json_db(DEPENDENCIES_DB_FILENAME)

  if versions_by_package is None:
    versions_by_package = generate_dict_versions_by_package(
        dependencies_by_dist)

  if conflicts_1_db is None and 1 in CONFLICT_MODELS:
    conflicts_1_db = load_json_db(DEPENDENCY_CONFLICTS1_DB_FILENAME)

  if conflicts_2_db is None and 2 in CONFLICT_MODELS:
    conflicts_2_db = load_json_db(DEPENDENCY_CONFLICTS2_DB_FILENAME)

  if conflicts_3_db is None and 3 in CONFLICT_MODELS:
    conflicts_3_db = load_json_db(DEPENDENCY_CONFLICTS3_DB_FILENAME)

  if blacklist is None:
    blacklist = load_json_db(BLACKLIST_DB_FILENAME)

  if include_edeps and elaborated_dependencies is None:
    elaborated_dependencies = load_json_db(ELAORATED_DEPS_FILENAME)



  # Trivial validation.
  # More detailed validation is now available with are_deps_valid, but it is
  # very slow even in non-thorough mode, and so I leave it to be manually
  # called where desired.

  assert type(dependencies_by_dist) is dict

  if 1 in CONFLICT_MODELS:
    assert type(conflicts_1_db) is dict
  if 2 in CONFLICT_MODELS:
    assert type(conflicts_2_db) is dict
  if 3 in CONFLICT_MODELS:
    assert type(conflicts_3_db) is dict

  assert type(blacklist) is dict






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
  outs = None
  try:
    outs = distkey[:distkey.find('(')].lower() 
  except AttributeError:
    print('Problematic distkey: ' + str(distkey))
    import ipdb
    ipdb.set_trace()
    raise Exception('POTATO')

  finally:
    return outs

  #return distkey[:distkey.find('(')].lower() # prophylactic lower





def get_version(distkey):
  """
  Note that the version string may contain parentheses. /:
  So it's just every character after the first '(' until the last
  character, which must be ')'.
  """
  return distkey[distkey.find('(') + 1 : -1].lower() # paranoid lower





def distkey_format(package_name, version_string):
  """
  Combine a package name and version string (e.g. 'django', '1.8.3') into a
  distkey e.g. 'django(1.8.3)'

  Reverse: get_pack_and_version()
  """
  return package_name.lower() + '(' + version_string.lower() + ')'





def is_valid_distkey(distkey, thorough=True):
  """
  Returns True if distkey is a valid distkey, else False.
  Data specifications in module docstring.
  If thorough is True (default), validates the version in the distkey by
  trying to create a pip version object with it.
  """

  try:
    packname = get_packname(distkey)
    version = get_version(distkey)
    
    # The first case here is a little strange because islower() returns False
    # if given a pure numeric string like '2112', which is actually legal for
    # package names.
    if not (distkey.islower() or distkey.lower() == distkey) or \
        distkey_format(packname, version) != distkey or \
        not distkey.find('(') + 1 < distkey.find(')') or \
        distkey[-1] != ')' or \
        '_' in packname:
      return False

    if thorough:
      pipified_version = pip._vendor.packaging.version.parse(version)

  except Exception:
    return False

  return True





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





def versions_are_equal(v1, v2):
  """
  Given two versions, each either strings or pip Version objects
  (pip._vendor.packaging.version.Version), returns True if both can be
  interpreted as the same version, within pip's sense of version strings.

  Raises (does not catch) pip._vendor.packaging.version.InvalidVersion if a
  given version cannot be interpreted by pip (BUT only if the arguments are not
  trivially identical to begin with, in which case doesn't bother with
  with conversion to pip Version objects.
  """
  # Given objects of same type that are identical.
  if type(v1) == type(v2) and v1 == v2:
    return True

  pipified1 = None
  pipified2 = None

  if isinstance(v1, pip._vendor.packaging.version._BaseVersion):
    pipified1 = v1
  else:
    pipified1 = pip._vendor.packaging.version.parse(v1)

  if isinstance(v1, pip._vendor.packaging.version._BaseVersion):
    pipified2 = v2
  else:
    pipified2 = pip._vendor.packaging.version.parse(v2)

  return pipified1 == pipified2





def fix_deps_case(deps):
  """
  Lowercase all package names in deps (dependers and depended-on).
  Onetime fix.
  """
  newdeps = dict()

  for distkey in deps:

    newdeps[distkey.lower()] = []

    for dep in deps[distkey]:
      packname = dep[0].lower()
      # '>=9.0DEV' is handled by the pip classes and identical to '>=9.0dev'
      specstring = dep[1] # not lower
      newdeps[distkey.lower()].append([packname, specstring])

  return newdeps





def assume_dep_data_exists_for(distkey, deps):
  """
  Raises depresolve.MissingDependencyInfoError if the given deps (or edeps)
  dictionary does not have an entry for the given distkey.
  """
  try:
    deps[distkey]
  except KeyError:
    raise depresolve.MissingDependencyInfoError('No dependency data for ' +
        distkey + ' in the dependencies dictionary.', distkey)





def is_dep_valid(dep, is_elaborated=False, thorough=False):
  """
  Returns False if the given dependency does not match the requirements
  specified in depdata.py for 'dep'.
  Else True.

  If is_elaborated is passed in as True, treats the dependency as an edep
  (see docstring at the top of depdata.py for dep vs edep). Defaults to dep.

  If thorough is passed in as True and is_elaborated is True, checks every
  single version string provided to make sure they're valid, by creating
  pip versions with them all.

  """

  log = depresolve.logging.getLogger('is_dep_valid')

  if thorough and not is_elaborated:
    raise ValueError('Calling with thorough on and is_elaborated off makes '
        'no sense. The thorough option is only for elaborated dependencies.')


  if (is_elaborated and len(dep) != 3) or \
      (not is_elaborated and len(dep) != 2):
    log.debug('dep not valid: dependency has wrong length '
        'for type: ' + 'not '*(not is_elaborated) + 'elaborated and len' +
        str(len(dep)))
    return False

  satisfying_packname = dep[0]
  specstring = dep[2] if is_elaborated else dep[1]
  satisfying_versions = dep[1] if is_elaborated else None

  if satisfying_packname.lower() != satisfying_packname:
    log.debug('dep not valid: package name ' + satisfying_packname + ' is not '
        'lowercase')
    return False

  # Could do another test here for validity of package names using safe_name
  # or something.

  try:
    specset = pip._vendor.packaging.specifiers.SpecifierSet(specstring)
  except:
    log.debug('dep not valid: specifier string ' + specstring + ' not valid '
        '(raised exception on attempt to create SpecifierSet with it).')
    return False


  if is_elaborated:
    if not isinstance(dep[1], list):
      log.debug('dep not valid: edep but 2nd item in a dep is not list.' +
          ' dep at issue: ' + str(dep))
      return False

    # If thorough is on, check every single version string in the elaborated
    # dependency. This is extremely slow for the entire set of dependencies!
    if thorough:
      for version in satisfying_versions: # Mind the None if you change this.
        try:
          pipified_version = pip._vendor.packaging.version.parse(version)
        except:
          log.debug('dep not valid: thorough: version ' + version +
              ' provided in dependency on ' + satisfying_packname + ' is  not '
              'a valid version.')
          return False

  return True





def are_deps_valid(deps, is_elaborated=False, thorough=False):
  """
  Returns False if the given dependencies dictionary does not match the
  following requirements:

   - deps must be a dependencies dictionary or elaborated dependencies
     dictionary as specified in depdata.py.

   - lowercase: all package names and distkeys must be lowercase. version
     specifiers are allowed to have any case.
      e.g. {'foo': ['bar', '>=1.0_A']} is fine
           {'Foo': ['bar', '']} is not OK because of the capitalization.

   - Each dep is a 2-length list (or, if edeps, a 3-length list).

  Running this on the full dependency data for PyPI takes about 8 seconds if
  thorough is off. With thorough on, this takes about 5 minutes!

  """
  log = depresolve.logging.getLogger('are_deps_valid')

  if not isinstance(deps, dict):
    log.debug('deps not valid: not a dictionary (or dict subclass)')
    return False

  for distkey in deps:

    if not is_valid_distkey(distkey, thorough):
      log.debug('deps not valid: invalid distkey: ' + distkey)
      return False

    if not isinstance(deps[distkey], list):
      log.debug('deps not valid: invalid dependency in deps (non-list) value')
      return False

    for dep in deps[distkey]:

      if not is_dep_valid(dep, is_elaborated, thorough):
        return False

  return True





def normalize_distkey(distkey):
  """
  Break apart the distkey and normalize its components before combining and
  returning the normalized key. (Unproven)
  """
  (packname, version) = get_pack_and_version(distkey)

  packname = normalize_package_name(packname)
  version = normalize_version_string(version)

  return distkey_format(packname, version)





def normalize_version_string(version):
  """
  Normalize version strings in the way that pip does.
  This must be tested against old normalization and data (blacklist, 
  conflicts?) must probably be converted.

  Note that pip._vendor.pkg_resources.safe_version does much less than pip
  does. pip employs a regex to handle certain version string components.
  """
  try:
    normalized = str(pip._vendor.packaging.version.parse(version))
  
  except pip._vendor.packaging.version.InvalidVersion:
    normalized = old_normalize_version_string(version)
    logger.debug('converting ' + version + ' via pip version class failed. '
      'using bandaid normalization: ' + old_normalize_version_string(version))

  finally:
    return normalized





def normalize_package_name(packname):
  """
  I am not confident that safe_name does adequate normalization of package
  names. It seems to me that the canonical names are lowercase, and safe_name
  doesn't do this. I could be wrong about that, but because safe_version very
  clearly does NOT normalize versions the way that pip does (pip does much
  more), I don't have a lot of confidence in safe_name either. Instead, I've
  just been replacing _ with - and calling lower. I hope the switch to using
  safe_name doesn't break things..... >.<
  """
  return packname.replace('_', '-').lower()
  #return pip._vendor.pkg_resources.safe_name(packname).lower()





def old_normalize_version_string(version):
  """
  EDIT: I believe I can now remove all of the below, but I'm already changing
  too much here, so I'll keep this for the next round of commits.

  This should normalize the version string the way that pip does it:
    str(pip._vendor.packaging.version.parse(raw_version_string))

  Obsolete code and comments follow, for now.

  # Simulate most of the normalization of version strings that occurs in pip.
  #from pip._vendor.pkg_resources import safe_name, safe_version #These don't quite do what I need, alas. Pip is doing more than just this. Ugh.
  #distutils.version.StrictVersion might match what I'm getting from within pip....
  # Nope. It helps in one case (1.01 -> 1.1), but hurts in many others.
    # Perform a variety of fixes to match pip's normalized package and version names,
    #   which are what my code inside pip spit out to the dbs.
    # So that our lookups work properly (and also to prevent continual reproduction
    #   of work), we'll account for these.
    # There are a few normalizations that pip appears to do.
    # The data being logged by my code within pip is being fed package names and versions
    #   normalized by some pip code, so we need to match our checks here to that
    #   normalization (which is unfortunately not entirely contained in safe_name or
    #   safe_version).
    #   pip can be expected to do:
    #   - underscores replaced by dashes
    #   - version string normalization via distutils.version.StrictVersion,
    #       which seems to match the information available to my code inside
    #       pip that's detecting the errors.
    #   Additionally, I'm going to work case-insensitive, and without assuming
    #     that existing data is all lowercase.
    # Some dist filenames have "_" where the package name has "-".
    # Versioning is slightly stricter inside pip. distutils.version.StrictVersion
    #   covers some of this normalization, but unfortunately not all of it. /:
    
    # Nevermind on the below: StrictVersion breaks other things, too. See daily notes (1.0.0 -> 1.0, unlike in pip)
    #try:
    #  # Example: AnyFilter-0.01 is treated as AnyFilter-0.1 in the pip code.
    #  # StrictVersion handles this category of correction for us.
    #  deduced_version_string = str(StrictVersion(deduced_version_string))
    #except ValueError:
    #  # If StrictVersion doesn't accept the string (e.g. if there's "dev" or "beta" in it, etc.), well,
    #  #   all we can do is some hackery for some cases in order to match what I see inside pip for now.
    #  # Maybe I can find the rest of the normalization somewhere, but it has already consumed time.
    #  # About 1/100 of my sample set has versions ending in "dev" that are then treated as "dev0" by pip.
    #  if deduced_version_string.endswith('dev)'): # Example: acted.projects(0.10.dev) is treated as acted.projects(0.10.dev0)
    #    deduced_version_string += "0"
    #  elif '-beta' in deduced_version_string: # Example: 2.0-beta5 is reported as 2.0b5 in the case of archgenxml
    #    deduced_version_string = deduced_version_string.replace('-beta','b')
  """
  # Example: about(0.1.0-alpha.1) is reported as about(0.1.0a1)
  # Dash removed, alpha to a, period after removed.    
  
  # 'dev' should always be preceded by a '.', not a '-'
  if '-dev' in version:
    version = version.replace('-dev', '.dev')
  elif '.dev' in version:
    pass
  elif 'dev' in version:
    version = version.replace('dev', '.dev')

  # 'dev' should not be followed by a '-'.
  # Example: abl.util-0.1.5dev-20111031 is treated as
  # abl.util(0.1.5.dev20111031), the dash removed and a '.' before dev.
  if 'dev-' in version:  
    version = version.replace('dev-', 'dev')


    # Remove preceding - or . from beta or alpha.
  # Example: 2.0-beta5 is reported as 2.0b5 in the case of archgenxml
  if '-beta' in version:  
    version = version.replace('-beta', 'beta')
  # Example: 2.0-beta5 is reported as 2.0b5 in the case of archgenxml
  if '.beta' in version:
    version = version.replace('.beta', 'beta')
  # Example: about(0.1.0-alpha.1) is reported as about(0.1.0a1)
  # Dash removed, alpha to a, period after removed.
  if '-alpha' in version:
    version = version.replace('-alpha', 'alpha')
  # Example: 'adpy(0.12.alpha0)' is treated as 'adpy(0.12a0)'
  if '.alpha' in version:
    version = version.replace('.alpha', 'alpha')

  # Remove . or ' following alpha or beta.
  # Example: about(0.1.0-alpha.1) is treated as about(0.1.0a1) by pip.
  if 'alpha.' in version:
    version = version.replace('alpha.', 'alpha')
  if 'alpha-' in version:
    version = version.replace('alpha-', 'alpha')
  if 'beta.' in version:
    version = version.replace('beta.', 'beta')
  if 'alpha-' in version:
    version = version.replace('beta-', 'beta')


  if version.endswith('dev') or version.endswith('beta') or \
    version.endswith('alpha'):
    # beta or alpha should always be followed by a number.
    # pip defaults to 0 in this case.
    # Example: acted.projects(0.10.dev) is treated as acted.projects(0.10.dev0)
    version += "0"


  # beta and alpha should be b and a
  # Doing this at the end may cause us to miss some cases in which (e.g.)
  # version strings already had a in place of alpha, but it also avoids us
  # messing up any hex strings with 'a's or 'b's in them NOT representing alpha
  # or beta....
  # For example, if the version string is '1.2a', code above will not have
  # correctly turned it into '1.2a0', unfortunately. But then we won't mess
  # with a version string (e.g. with commit hash in it) ending with 'a351b8a'
  # by incorrectly adding a 0 to it.
  # Compromises....
  if 'beta' in version: # beta should always be b instead.
    version = version.replace('beta', 'b')
  if 'alpha' in version: # beta should always be b instead.
    version = version.replace('alpha', 'a')

  # This is awkward, but it covers a sizeable number of cases.
  if '.00' in version:
    version = version.replace('.00', '.0')
  if '.01' in version:
    version = version.replace('.01', '.1')
  if '.02' in version:
    version = version.replace('.02', '.2')
  if '.03' in version:
    version = version.replace('.03', '.3')
  if '.04' in version:
    version = version.replace('.04', '.4')
  if '.05' in version:
    version = version.replace('.05', '.5')
  if '.06' in version:
    version = version.replace('.06', '.6')
  if '.07' in version:
    version = version.replace('.07', '.7')
  if '.08' in version:
    version = version.replace('.08', '.8')
  if '.09' in version:
    version = version.replace('.09', '.9')


    return version





def spectuples_to_specset(list_of_spectuples):
  """
  This provides compatibility with an old format of dependency data.

  Arguments:
     1. A list of specifiers in the form of 2-tuples, operator and version.
        e.g., for the specification of any version between 0.4.0 and
        0.6.6, not inclusive:
        [ [ '>', '0.4.0' ], ['<', '0.6.6'] ]
  
  Returns:
    1. A corresponding SpecifierSet object
       e.g.:
        <SpecifierSet('<0.6.6,>0.4.0')>

    2. For convenience, a string in the format that the SpecifierSet
       constructor takes.
       e.g.:
       '<0.6.6,>0.4.0'
  
  SpecifierSet comes from module pip._vendor.packaging.specifiers.

  """
  # Catenate the specifier sets back together.
  specstring = spectuples_to_specstring(list_of_spectuples)

  return pip._vendor.packaging.specifiers.SpecifierSet(specstring), specstring





def spectuples_to_specstring(list_of_spectuples):
  """
  This provides compatibility with an old format of dependency data.

  See spectuples_to_specset for some more details.

  Given   [ ['>=', '2'], ['<', '4'] ]
  Returns '>=2,<4'

  Given   [ ['>=', '2'] ]
  Returns '>=2'

  Given   []
  Returns ''

  """
  # Catenate the specifier set back together.
  specstring = ''
  # for each specification (example specification: [ '>', '0.4.0' ]) in the
  # list of specs:
  for specification in list_of_spectuples:
    # append the operator and operand (version string) back together, with
    # distinct specifiers separated by commas.
    specstring += specification[0] + specification[1] + ','

  # Trim trailing comma after loop.
  if specstring.endswith(','):
    specstring = specstring[:-1]

  return specstring





def generate_dict_versions_by_package(deps):
  """
  Given a dictionary of the dependencies of dists (keyed with dist keys, e.g.
  'django(1.8.3)'), generates a dictionary of all versions of all packages for
  which we have dependency information.

  Argument:
    1. deps: dependency info in the form of a dictionary, keys being distkeys
       and values being 'dep' elements, as defined in the docstrings of other
       functions (TODO: consolidate). (elaborated dependencies also work.)
       e.g.:
         {'motorengine(0.7.4)': 
            [  ['pymongo', '==2.5'],
               ['tornado', ''],
               ['motor', ''],
               ['six', ''],
               ['easydict', '']
            ],
          'django(1.8.3)':
            [],
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

    Returns:
      1. versions_by_package, a dictionary keyed by package name and valued
         with a list of of versions of that package (that appear in the deps
         dictionary - that we have dependency information for, in other words).
         e.g.
            {
              'django': ['1.8.3', '1.6.3', '1.7'],
              'motorengine': ['0.7.4'],
              'chembl-webservices': ['2.2.11']
            }

  """
  versions_by_package = dict()

  # Enumerate all package names (not versions but distinct packages).
  # "distkey" here is a string of the form 'codegrapher(0.1.1)'
  # "packagename" would then be 'codegrapher'
  # For each key (dist) in the dependency db:
  for distkey in deps:
    (packagename, version) = get_pack_and_version(distkey)

    try:
      versions_by_package[packagename].append(version)
    except KeyError:
      versions_by_package[packagename] = [version]

  return versions_by_package





def elaborate_dependencies(deps, versions_by_package):
  """
  Converts deps (see description of deps in previous docstrings) into a
  dictionary of all possible means of satisfying each dependency, by using
  the list of all versions of all packages (versions_by_package) combined with
  the filter implicit in the version ranges in deps entries.

  This is done by parsing version constraints in each dependency in deps into a
  SpecifierSet, from pip._vendor.packaging.specifiers.SpecifierSet, and using
  that SpecifierSet to filter the list of all versions available for the
  package depended on.

  Creation of a SpecifierSet requires that an input string have the form of
  these examples:
    '>=1.3,<3.0'
    '==2.5'
    '<4.0'
  SpecifierSet has a method, filter(), that will take a list of versions and
  spit back only the ones that fit the constraints of the Specifiers.

  In the end, we'll have gone...
    from this        into this
    ------------     -------------------------------------
    '>=3.0'          ['3.0', '3.1', '3.2', '3.3', '4']
    '==1.0'          ['1.0']
    ''               ['1', '2.0', '2.5', '3.0', '3.1', '3.2', '3.3', '4']
    '>1,<3.1'        ['2.0', '2.5', '3.0']


  Running this on dependency data (package names and specifier strings) for
  300,000 packages from PyPI takes on the order of 20 minutes.


  Argument:
    1. deps, dependency info in the form of a dictionary. Please see other
       docstrings for information on "deps", for example
       _generate_dict_versions_by_package()
       For this docstring's example, we start with deps containing an entry:
       deps['codegrapher(0.1.1)']  = [
           [ 'click', '>=1.0,<4.1'],
           [ 'graphviz', '' ],
       ]

    2. versions_by_package, a dictionary of all dists keyed by package name.
       Please see docstrings above for details.


  Returns:
    1. deps_elaborated, a dictionary keyed by distkey with values each equal to
       a tuple containing four elements, the 3-tuple returned by helper
       _elaborate_dependency(). See _elaborate_dependency() for details.
       
       Here is an example, though:
       Imagine that version 0.1.1 of codegrapher depends on click >= 1.0 and
       any version of graphviz. We would see this in the returned dictionary:

        deps_elaborated['codegrapher(0.1.1)']  = 
        [
            (
                'click',
                [  '1.0', '1.1', '2.0', '2.1', '2.2', '2.3', '2.4', '2.5',
                   '2.6', '3.0', '3.1', '3.2', '3.3', '4.0', '4.1'  ],
                '>=1.0'
            ),
            (
                'graphviz',
                [ '0.4.7' ],
                ''
            )
        ]

    2. packages_without_available_version_info, a set() of package names
       for which the list of known versions is not available.

    3. dists_with_missing_dependencies, a set() of dists which depend on a
       package in packages_without_available_version_info (that is, the set of
       dists which have a dependency which we can't elaborate due to a lack of
       information on the available versions of the satisfying package).
  """

  log = depresolve.logging.getLogger('elaborate_dependencies')

  deps_elaborated = dict()

  # The set of all package names for which we do not have a list of available
  # versions.
  packages_without_available_version_info = set()

  # The set of all dists for which one or more of their dependencies could not
  # be enumerated. (i.e. a list of all dists depending on a package whose name
  # is in packages_without_available_version_info)
  dists_with_missing_dependencies = set()

  DEBUG_index_packages = 0
  DEBUG_index_dependencies = 0
  #DEBUG_STOP_AFTER_X_PACKAGES = 10000

  # For each key (dist) in the dependency db:
  for distkey in deps:

    # DEBUG SECTION
    DEBUG_index_packages += 1
    DEBUG_index_dependencies = 0
    #if DEBUG_index_packages > DEBUG_STOP_AFTER_X_PACKAGES:
    #  break
    log.debug("    Elaborating dependencies for " + str(DEBUG_index_packages)
        + "th package: " + distkey)
    # END OF DEBUG SECTION


    deps_elaborated[distkey] = []

    for dep in deps[distkey]:
      
      # DEBUG SECTION
      DEBUG_index_dependencies += 1
      #log.info("        Elaborating " + str(DEBUG_index_dependencies) + "th "
      #    "dependency of " + distkey + ": on package " + dep[0])
      # END OF DEBUG SECTION

      e_dep = _elaborate_dependency(dep, versions_by_package)

      deps_elaborated[distkey].append(e_dep)

      if e_dep[1] == PACKAGE_VERSIONS_UNKNOWN:
        packages_without_available_version_info.add(dep[0])
        dists_with_missing_dependencies.add(distkey)

  return (
      deps_elaborated,
      packages_without_available_version_info, 
      dists_with_missing_dependencies
  )





def _elaborate_dependency(dep, versions_by_package):
  """
  Given a single dependency in post-pip format, return its specifier string,
  SpecifierSet, and the full set of elaborated dependencies (a list of every
  dist key that could individually satisfy the given dependency).

  Arguments:
    1. dep, the format of dependency information generated by my pip code.
       This specifies the range of versions of a single package, that would
       satisfy some dependency of another package. Note that a "dep" here is
       a single value in the "deps" dictionary defined in other docstrings
       above. In particular, "dep" is:
         a 2-tuple containing:
           A. package name
           B. list of 2-tuples, each tuple constituting a specifier:
                1. operator ('>', '>=', '==', '<', '<=', or ''
                2. version (e.g. '1.4')
       e.g.: for a dependency on a version of motor between 0.4.0 and 0.6.6:
         ('motor',                # package name
          '>0.4.0,<0.6.6' ]     # specifier string
         )
        indicating: depends on motor, version > 0.4.0 and < 0.6.6

    2. versions_by_package, a dictionary with keys equal to all package names,
       and values equal to lists of all versions available for those packages.

  Returns:
    Returns None if a list of package versions could not be found in
    versions_by_package.

    Otherwise, returns a 3-tuple:
    1. The name of the package depended on (e.g. 'django')

    2. The elaboration: a list of every dist key (package version identifier)
       that would satisfy the given dependency.
       e.g., if the given dependency is on django >= 1.8.3 and <= 1.8.6:
         ['django(1.8.3)', 'django(1.8.4)', 'django(1.8.5)', 'django(1.8.6)']

       This list is instead set to PACKAGE_VERSIONS_UNKNOWN if there is no
       entry in versions_by_package for the package needed to satisfy the
       dependency. (In other words, if we don't have a list of available
       versions for the package needed, item 2 = PACKAGE_VERSIONS_UNKNOWN.)

    3. A dependency specifier string characterizing the version range for this
       dependency, in the format required by pip._vendor.packaging.specifiers.
       (Now the same as the specifier string from argument dep above)
       e.g.:
         '>0.4.0,<0.6.6'

  """
  # Interpret the dependency as a package name and SpecifierSet.
  satisfying_packagename = dep[0]
  specstring = dep[1]
  specset = pip._vendor.packaging.specifiers.SpecifierSet(specstring)
  # Now we have a SpecifierSet for this dependency.

  # One of the capabilities of pip's SpecifierSet is to filter a list of
  # version strings, returning only those that satisfy. We will be applying
  # this filter to the list of available versions of the given package. The
  # result of the filtering will be all of the version satisfying the
  # dependency.
  
  # During debugging, we're working with a reduced database of packages,
  # so we may not have dependency info for the particular package. If we
  # don't, add that package to the list of packages we don't know about
  # yet.

  try:
    # Do we have a list of the versions available for the package depended on?
    versions_by_package[satisfying_packagename]

  except KeyError:
    #log.info("--Package " + distkey + " depends on " + satisfying_packagename +
    #  ", but we don't have dependency data on " + satisfying_packagename +
    #  ". Skipping and leaving that dependency empty. This should not"
    #  " happen with a complete dependency database!")
    filtered_versions = PACKAGE_VERSIONS_UNKNOWN

  else:
    filtered_versions = [version for version in 
        specset.filter(versions_by_package[satisfying_packagename])]
    #log.info("--Successfully elaborated dependency.")

  return (satisfying_packagename, filtered_versions, specstring)#, specset)





# Toy
def get_dependencies_of_all_X_on_Y(depender_pack, satisfying_pack, deps,
    versions_by_package=None):
  """
  Just a toy function for debugging, not likely to be of use in the module
  itself.
  Given a depender package name and a satisfying package name, map each version
  of the depender to the specifier string distinguishing acceptable versions of
  the satisfying package.
  
  e.g.:
  get_dependencies_of_all_X_on_Y('motor', 'pymongo', deps, versions_by_package)
    returns:
      ['motor(0.5b0): ==2.8.0',
       'motor(0.5): ==2.8.0',
       'motor(0.4.1): ==2.8.0',
       'motor(0.4): ==2.8.0',
       'motor(0.3.4): ==2.7.1',
       'motor(0.3.3): ==2.7.1',
       'motor(0.3.2): ==2.7.1',
       'motor(0.3.1): ==2.7.1',
       'motor(0.3): ==2.7.1',
       'motor(0.2.1): ==2.7',
       'motor(0.2): ==2.7',
       'motor(0.1.2): ==2.5.0',
       'motor(0.1.1): ==2.5.0',
       'motor(0.1): >=2.4.2',
       'motor(0.0-): >=2.4.2']

  Throws:
    - MissingDependencyInfoError if the given package names do not appear in
      the given deps (/ versions_by_package) info.

  """
  if versions_by_package is None:
    versions_by_package = deptools.generate_dict_versions_by_package(deps)

  dependencies = []
  if depender_pack not in versions_by_package or satisfying_pack not in \
      versions_by_package:
    raise depresolve.MissingDependencyInfoError('Given package names ' + 
        depender_pack + ' and ' + satisfying_pack + ' do not both appear in '
        'the dependency info provided.')

  for version in sorted(versions_by_package[depender_pack], reverse=True):
    depender_distkey = distkey_format(depender_pack, version)

    assume_dep_data_exists_for(depender_distkey, deps)

    depstring_for_v_x_on_pack_y = None

    for dep in deps[depender_distkey]:
      if dep[0] == satisfying_pack:
        depstring_for_v_x_on_pack_y = dep[1]

    if depstring_for_v_x_on_pack_y:
      dependencies.append(
          depender_distkey + ': ' + depstring_for_v_x_on_pack_y)
    else:
      dependencies.append(
          depender_distkey + ' does not depend on ' + satisfying_pack)

  return dependencies



