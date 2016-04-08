"""
<Program Name>
  Dependency Tools

<Purpose>
  Provide functions for dealing with dependency data generated by
  analyze_deps_from_pip.


<Functions>

  Public:

      load_raw_deps_from_sql                  ()

      load_raw_deps_from_json                 ()

      populate_sql_with_full_dependency_info  (
                                      deps_elaborated,
                                      versions_by_package,
                                      packages_without_available_version_info,
                                      dists_with_missing_dependencies)

      generate_dict_versions_by_package       (deps)

      elaborate_dependencies                  (deps, versions_by_package)
      spectuples_to_specset                   (spectuples)
      spectuples_to_specstring                (spectuples)


  Internal:
      _elaborate_dependency                   (dep, versions_by_package)
      _convert_to_specifierset                (list_of_spec_tuples)



Example usage:

    deps = deptools.load_raw_deps_from_json()

    # First, I need a dict of available package versions given package name P.
    versions_by_package = deptools.generate_dict_versions_by_package(deps)

    # Elaborate deps into lists of specific satisfactory versions.
    # We'll parse the version constraints in the dependency into a
    # SpecifierSet, from pip._vendor.packaging.specifiers.SpecifierSet along
    # the way.
    (
        deps_elaborated,
        packages_without_available_version_info,
        dists_with_missing_dependencies
    ) = deptools.elaborate_dependencies(deps, versions_by_package)

    # Feed this into the sqlite tables.
    deptools.populate_sql_with_full_dependency_info(
        deps_elaborated,
        versions_by_package,
        packages_without_available_version_info,
        dists_with_missing_dependencies)

"""

import resolver # __init__ for errors
import os      # for path joins
import json    # the dependency db we'll read is in a json
import logging
logging.basicConfig(filename='resolver.log',level=logging.DEBUG)
import pip._vendor.packaging.specifiers # for SpecifierSet for version parsing

import resolver.resolver_sqli as sqli # the resolver's sqlite module


# Local resources for the resolver package.
WORKING_DIRECTORY = os.getcwd() #'/Users/s/w/git/pypi-depresolve' in my setup
DEPENDENCIES_DB_FILENAME = os.path.join(WORKING_DIRECTORY, '..',
    "dependencies_db.json")
#DEPENDENCY_CONFLICTS3_DB_FILENAME = os.path.join(WORKING_DIRECTORY,
#    "conflicts_3_db.json") # db for model 3 conflicts
#DEPENDENCIES_DB_ELABORATED_FILENAME = os.path.join(WORKING_DIRECTORY,
#    "dependencies_db_elaborated.json")
#DEPENDENCIES_DB_MISSING_FILENAME = os.path.join(WORKING_DIRECTORY,
#    "dependencies_db_missing.json")
PACKAGE_VERSIONS_UNKNOWN = ['----ERROR--UNAVAILABLE-VERSION-INFORMATION----']

def load_raw_deps_from_sql():
  """"""
  assert False, "Not written yet"






def load_raw_deps_from_json(deps_db_fname=DEPENDENCIES_DB_FILENAME):
  """
  Import dependency information and conflict information from json files that
  were created by my modified pip fork and analyze_deps_via_pip.py script.
  """
  deps = json.load(open(deps_db_fname, 'r'))
  #confs = json.load(open(DEPENDENCY_CONFLICTS3_DB_FILENAME, 'r'))
  return deps





def populate_sql_with_full_dependency_info(
    deps_elaborated,
    versions_by_package,
    packages_without_available_version_info,
    dists_with_missing_dependencies,
    db_fname=None):
  """
  (Write this docstring last.)
  """
  log = logging.getLogger('populate_sql_with_full_dependency_info')

  log.info("Initializing db")

  # Initialize the sqlite3 database that will be populated with dependency
  # information as interpreted from the json files above.
  sqli.initialize(db_fname)

  for distkey in deps_elaborated: # for every dist,

    log.info("Working through " + distkey + "'s dependencies.")
    for e_dep in deps_elaborated[distkey]: # for every one of its dependencies,

      satisfying_packagename = e_dep[0]
      list_of_satisfying_versions = e_dep[1]
      specstring = e_dep[2]
      # We don't need the SpecifierSet, element 3 (4th) of the tuple right now.

      log.info("  satisfying_packagename:" + satisfying_packagename)
      log.info("  list_of_satisfying_versions: " + str(list_of_satisfying_versions))
      log.info("  specstring: " + specstring)

      # First, let's add the dependency specifier to that table.
      sqli.add_to_table(
          sqli.SQL_DEP_SPECIFIER_TABLENAME,
          distkey,
          satisfying_packagename,
          specstring
          )

      # Now let's add every satisfying version to the full dependency info
      # table.
      for version in list_of_satisfying_versions:
        satisfying_distkey = get_distkey(satisfying_packagename, version)

        sqli.add_to_table(
            sqli.SQL_DEPENDENCY_TABLENAME,
            distkey, # depending dist: 'codegrapher(0.1.1)'
            satisfying_packagename, # package depended on: 'click'
            satisfying_distkey # one distkey that could satisfy: 'click(1.0)'
        )

  sqli.flush()






def generate_dict_versions_by_package(deps):
  """
  Given a dictionary of the dependencies of dists (keyed with dist keys, e.g.
  'django(1.8.3)'), generates a dictionary of all versions of all packages for
  which we have dependency information.

  Argument:
    1. deps: dependency info in the form of a dictionary, keys being distkeys
       and values being 'dep' elements, as defined in the docstrings of other
       functions (TODO: consolidate).
       e.g.:
         {'motorengine(0.7.4)': 
            [  ['pymongo', [['==', '2.5']]],
               ['tornado', []],
               ['motor', []],
               ['six', []],
               ['easydict', []]
            ],
          'django(1.8.3)':
            [],
          'django(1.6.3)':
            [],
          'django(1.7)':
            [],
          'chembl-webservices(2.2.11)':
            [  ['lxml', []],
               ['pyyaml', [['>=', '3.10']]],
               ['defusedxml', [['>=', '0.4.1']]],
               ['simplejson', [['==', '2.3.2']]],
               ['pillow', [['>=', '2.1.0']]],
               ['django-tastypie', [['==', '0.10']]],
               ['chembl-core-model', [['>=', '0.6.2']]],
               ['cairocffi', [['>=', '0.5.1']]],
               ['numpy', [['>=', '1.7.1']]],
               ['mimeparse', []],
               ['raven', [['>=', '3.5.0']]],
               ['chembl-beaker', [['>=', '0.5.34']]
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


  Argument:
    1. deps, dependency info in the form of a dictionary. Please see other
       docstrings for information on "deps", for example
       _generate_dict_versions_by_package()
       For this docstring's example, we start with deps containing an entry:
       deps['codegrapher(0.1.1)']  = [
           [ 'click', [
                        ['>=', '1.0'],
                        ['<',  '4.1']
                      ]
           ],
           [ 'graphviz', [] ],
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

    2. packages_without_available_version_info, a simple list of package names
       for which the list of known versions is not available.

    3. dists_with_missing_dependencies, a list of dists which depend on a
       package in packages_without_available_version_info (that is, a list of
       dists which have a dependency which we can't elaborate due to a lack of
       information on the available versions).
  """

  log = logging.getLogger('elaborate_dependencies')

  deps_elaborated = dict()

  # A list of all package names for which we do not have a list of available
  # versions.
  packages_without_available_version_info = []

  # A list of all dists for which one or more of their dependencies could not
  # be enumerated. (i.e. a list of all dists depending on a package whose name
  # is in packages_without_available_version_info)
  dists_with_missing_dependencies = []

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
    log.info("    Elaborating dependencies for " + str(DEBUG_index_packages)
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
        packages_without_available_version_info.append(dep[0])
        dists_with_missing_dependencies.append(distkey)

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
         ('motor',                  # The package name
           [  [ '>', '0.4.0' ],     # specifier: versions > 0.4.0
              [ '<', '0.6.6' ]      # specifier: versions < 0.6.6
           ]
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
       e.g.:
         '>0.4.0,<0.6.6'

    Note that item 3 is somewhat redundant and provided for convenience/debug.

  """

  #log = logging.getLogger('_elaborate_dependency')

  # Interpret the dependency as a package name and SpecifierSet.
  satisfying_packagename = dep[0]
  list_of_spec_tuples = dep[1]
  (specset, specstring) = spectuples_to_specset(list_of_spec_tuples)
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





# pip-connecting utility functions
def spectuples_to_specset(list_of_spectuples):
  """

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



# Toy
def get_dependencies_of_all_X_on_Y(depender_pack, satisfying_pack, deps,
    versions_by_package):
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
  """
  return [distkey + ": " + [spectuples_to_specstring(dep[1]) for \
      dep in deps[distkey] if dep[0] == satisfying_pack][0] for \
      distkey in [get_distkey(depender_pack, version) for version in versions_by_package[depender_pack]]]




# General purpose utility functions.
def get_pack_and_version(distkey):
  """
  Convert a distkey, e.g. 'django(1.8.3)', into a package name and
  version string, e.g. ('django', '1.8.3').

  Reverse: get_distkey()
  """
  # The package name ends with the first open parenthesis.
  packagename = distkey[:distkey.find('(')]
  # Note that the version string may contain parentheses. /:
  # So it's just every character after the first '(' until the last
  # character, which must be ')'.
  version = distkey[distkey.find('(') + 1 : -1]
  return (packagename, version)




def get_distkey(package_name, version_string):
  """
  Combine a package name and version string (e.g. 'django', '1.8.3') into a
  distkey e.g. 'django(1.8.3)'

  Reverse: get_pack_and_version()
  """
  return package_name + '(' + version_string + ')'
