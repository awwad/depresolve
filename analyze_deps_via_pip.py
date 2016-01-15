# <~>
# Employs custom version of pip (awwad/pip:develop) to harvest dependencies and find dependency conflicts for packages in PyPI.
# See README.md!

import sys # for arguments and exceptions
import pip
import os
import json
#import ipdb
from distutils.version import StrictVersion, LooseVersion # for use in version parsing

# Local resources
BANDERSNATCH_MIRROR_DIR = '/srv/pypi/web/packages/source/'
LOCATION_OF_LOCAL_INDEX_SIMPLE_LISTING = 'file:///srv/pypi/web/simple'
WORKING_DIRECTORY = os.getcwd() #'/Users/s/w/git/pypi-depresolve' in my setup
DEPENDENCY_CONFLICTS1_DB_FILENAME = os.path.join(WORKING_DIRECTORY, "conflicts_1_db.json") # db for model 1 conflicts
DEPENDENCY_CONFLICTS2_DB_FILENAME = os.path.join(WORKING_DIRECTORY, "conflicts_2_db.json") # db for model 2 conflicts
DEPENDENCY_CONFLICTS3_DB_FILENAME = os.path.join(WORKING_DIRECTORY, "conflicts_3_db.json") # db for model 3 conflicts
BLACKLIST_DB_FILENAME = os.path.join(WORKING_DIRECTORY, "blacklist_db.json")
DEPENDENCIES_DB_FILENAME = os.path.join(WORKING_DIRECTORY, "dependencies_db.json")
TEMPDIR_FOR_DOWNLOADED_DISTROS = os.path.join(WORKING_DIRECTORY, 'temp_distros') # May not want this in same place as working directory. Would be terrible to duplicate. One such sdist cache per system! Gets big.
# If temp / output files are added, please ensure that the directories they're in are also added to this list:
LIST_OF_OUTPUT_FILE_DIRS = [TEMPDIR_FOR_DOWNLOADED_DISTROS, os.path.dirname(BLACKLIST_DB_FILENAME), os.path.dirname(DEPENDENCY_CONFLICTS3_DB_FILENAME), os.path.dirname(DEPENDENCY_CONFLICTS2_DB_FILENAME), os.path.dirname(DEPENDENCY_CONFLICTS1_DB_FILENAME), os.path.dirname(DEPENDENCIES_DB_FILENAME)]

# Other Assumptions
SDIST_FILE_EXTENSION = '.tar.gz' # assume the archived packages bandersnatch grabs end in this
DISABLE_PIP_VERSION_CHECK = '--disable-pip-version-check' # argument to pass to pip to tell it not to prod users about our strange pip version (lest they follow that instruction and install a standard pip version)

# Ensure that appropriate directories for working files / output files exist.
# Becomes relevant whenever those are placed elsewhere.
assert(os.path.exists(WORKING_DIRECTORY))
for dirname in LIST_OF_OUTPUT_FILE_DIRS:
  if not os.path.exists(dirname):
    os.makedirs(dirname)
    print("Directory check: " + dirname + " does not exist. Making it.")

# Argument handling:
#  DEPENDENCY CONFLICT MODELS (see README)
#   --cm1    run using conflict model 1 (all resolvable and unresolvable conflicts; see README)
#   --cm2    run using conflict model 2 (all unresolvable and some resolvable conflicts; see README)
#   --cm3    run using conflict model 3 (default; basically "would pip get this right?"; see README)
#
#  GENERAL ARGUMENTS:
#   --noskip Don't skip packages in the blacklist or packages for which information on
#            whether or not a conflict occurs is already stored.
#
#  REMOTE OPERATION:   (DEFAULT!)
#    ANY ARGS NOT MATCHING the other patterns are interpreted as what I will refer to as 'distkeys':
#      packagename(packageversion)
#      e.g.:   "django(1.8)"
#      Using one of these means we're downloading from PyPI, per pip's defaults.
#      Your shell will presumably want these arguments passed in quotes because of the parentheses.
#
#
#  LOCAL OPERATION: For use when operating with local sdist files (e.g. with a bandersnatched local PyPI mirror)
#   --local=FNAME  specifies a local .tar.gz sdist to inspect for dependency conflicts with pip
#                  for dependency conflicts
#                  e.g. '--local=/srv/pypi/web/packages/source/M/motorengine/motorengine-0.7.4.tar.gz'
#                  You can specify as many of these as you like with separate --local=<file> arguments.
#                  Local and remote execution are mutually exclusive.
#   --local  Using this without "=<file.tar.gz>" means we should alphabetically scan from the local PyPI mirror.
#            This is mutually exclusive with the --local=<fname> usage above. If files are specified, we only
#            check the files specified.
#   
#   --n=N    For use only with --local (not remotes, not --local=<file>).
#            Sets N as the max packages to inspect when pulling alphabetically from local PyPI mirror.
#            e.g. --n=1  or  --n=10000
#            Default for --local runs, if this arg is not specified, is all packages in the entire local PyPI
#            mirror at /srv/pypi)
#            (TODO: Must confirm that using this arg won't impact remote operation, just for cleanliness.)
#
#
#
#   EXAMPLE CALLS:
#
#      ~~ Run on a single package (in this case, arnold version 0.3.0) pulled from remote PyPI,
#         using conflict model 3 (default):
#
#          >  python analyze_deps_via_pip.py "arnold(0.3.0)"
#
#
#      ~~ Run on a few packages from PyPI, using conflict model 2, and without skipping even if
#         conflict info on those packages is already available, or if they're in the blacklist for
#         having hit unexpected errors in previous runs:
#
#          >  python analyze_deps_via_pip.py "motorengine(0.7.4)" "django(1.6.3)" --cm2 --noskip
#
#
#      ~~ Run on a single specified package, motorengine 0.7.4, stored locally, using conflict model 2:
#           
#          >  python analyze_deps_via_pip.py --cm2 --local=/srv/pypi/web/packages/source/M/motorengine/motorengine-0.7.4.tar.gz
#
#      ~~ Run on the first 10 packages in the local pypi mirror (assumed /srv/pypi) alphabetically,
#          using conflict model 1.
#
#          >  python analyze_deps_via_pip.py --cm1 --local --n=10
#
def main():
  DEBUG__N_SDISTS_TO_PROCESS = 0 # debug; max packages to explore during debug - overriden by --n=N argument.
  CONFLICT_MODEL = 3
  NO_SKIP = False
  USE_BANDERSNATCH_MIRROR = False

  print("analyze_deps_via_pip - Version 0.3")
  list_of_sdists_to_inspect = [] # potentially filled with local sdist filenames, from arguments
  list_of_remotes_to_inspect = [] # potentially filled with remote packages to check, from arguments

  # Argument processing. If we have arguments coming in, treat those as the packages to inspect.
  if len(sys.argv) > 1:
    for arg in sys.argv[1:]:
      if arg.startswith("--n="):
        DEBUG__N_SDISTS_TO_PROCESS = int(arg[4:])
      elif arg == "--cm1":
        CONFLICT_MODEL = 1
      elif arg == "--cm2":
        CONFLICT_MODEL = 2
      elif arg == "--cm3":
        CONFLICT_MODEL = 3
      elif arg == "--noskip":
        NO_SKIP = True
      elif arg == "--local":  # without ='<some file>' means we pull alphabetically from local PyPI mirror at /srv/pypi/
        USE_BANDERSNATCH_MIRROR = True
      elif arg.startswith("--local="):
        list_of_sdists_to_inspect.append(arg[8:]) # e.g. '--local=/srv/pypi/web/packages/source/M/motorengine/motorengine-0.7.4.tar.gz'
        USE_BANDERSNATCH_MIRROR = True
      else:
        list_of_remotes_to_inspect.append(arg) # e.g. 'motorengine(0.7.4)'
        USE_BANDERSNATCH_MIRROR = False # For simplicity right now, I'll use one mode or another, not both. Last arg has it if both.

  # If we were told to work with a local mirror, but weren't given specific sdists to inspect,
  #   we'll scan everything in BANDERSNATCH_MIRROR_DIR until we have DEBUG__N_SDISTS_TO_PROCESS
  #   sdists.
  if USE_BANDERSNATCH_MIRROR and not list_of_sdists_to_inspect:
    # Ensure that the local PyPI mirror directory exists first.
    if not os.path.exists(BANDERSNATCH_MIRROR_DIR):
      raise Exception('<~> Exception. Expecting a bandersnatched mirror of PyPI at ' + BANDERSNATCH_MIRROR_DIR + ' but that directory does not exist.')
    i = 0
    for dir, subdirs, files in os.walk(BANDERSNATCH_MIRROR_DIR):
      for fname in files:
        if is_sdist(fname):
          list_of_sdists_to_inspect.append(os.path.join(dir, fname))
          i += 1
          if i >= DEBUG__N_SDISTS_TO_PROCESS: # awkward control structure, but saving debug run time. tidy later.
            break
      if i >= DEBUG__N_SDISTS_TO_PROCESS: # awkward control structure, but saving debug run time. tidy later.
        break

  # Fetch info on already known conflicts so that we can skip packages below.
  conflicts_db_fname = None
  if CONFLICT_MODEL == 1:
    conflicts_db_fname = DEPENDENCY_CONFLICTS1_DB_FILENAME
  elif CONFLICT_MODEL == 2:
    conflicts_db_fname = DEPENDENCY_CONFLICTS2_DB_FILENAME
  else:
    assert(CONFLICT_MODEL == 3)
    conflicts_db_fname = DEPENDENCY_CONFLICTS3_DB_FILENAME

  conflicts_db = load_json_db(conflicts_db_fname)

  # For backward compatibility (before casing fixes for certain package names):
  #   Determine a lower-cased set of the keys in the conflicts db.
  keys_in_conflicts_db_lower = set(k.lower() for k in conflicts_db)

  # Fetch info on packages in the blacklist.
  # These are runs that resulted in errors or runs that were manually added
  #   because, for example, they hang seemingly forever or take an inordinate length of time.
  # Because this came abount after casing resolution addressed above,
  #   I know there are no non-lower keys in it. TODO: Write integration/validation tests for casing.
  blacklist_db = load_json_db(BLACKLIST_DB_FILENAME)
  

  n_inspected = 0
  n_added_to_blacklist = 0

  # Generate a list of distkeys (e.g. 'django(1.8.3)') to inspect, from the lists of sdists and "remotes".
  distkeys_to_inspect = []
  if USE_BANDERSNATCH_MIRROR:
    for tarfilename_full in list_of_sdists_to_inspect:

      # Deduce package names and versions from sdist filename.
      packagename = get_package_name_given_full_filename(tarfilename_full)
      packagename_withversion = get_package_and_version_string_from_full_filename(tarfilename_full)
      deduced_version_string = packagename_withversion[len(packagename) + 1:]

      # Perform a variety of fixes to match pip's normalized package and version names,
      #   which are what my code inside pip spits out to the dbs.
      deduced_version_string = normalize_version_string(deduced_version_string)
      distkey = packagename + "(" + deduced_version_string + ")" # This is the format for dists in the conflict db.
      distkey = distkey.lower().replace('_', '-')
      
      distkeys_to_inspect.append(distkey)
      
  else: # if not using local bandersnatched PyPI mirror
    for distkey in list_of_remotes_to_inspect:
      assert '(' in distkey and distkey.endswith(')'), "Invalid input."
      distkey = distkey.lower().replace('_', '-') # avoid casing issues and incorrect underscores
      distkeys_to_inspect.append(distkey)
    


  # Now take all of the distkeys ( e.g. 'python-twitter(0.2.1)' ) indicated and run on them.
  for distkey in distkeys_to_inspect:
    
    # Check to see if we already have conflict info for this package. If so, don't run for it.

    if not NO_SKIP:
      if distkey in keys_in_conflicts_db_lower:
        n_inspected += 1
        print("<~>    SKIP -- Already have " + distkey + " in db of type " + str(CONFLICT_MODEL) + " conflicts. Skipping. (Now at " + str(n_inspected) + " out of " + str(len(list_of_sdists_to_inspect)) + ")")
        continue
      # Else if the dist is listed in the blacklist along with this python major version (2 or 3), skip.
      elif distkey in blacklist_db and sys.version_info.major in blacklist_db[distkey]:
        n_inspected += 1
        print("<~>    SKIP -- Blacklist includes " + distkey + ". Skipping. (Now at " + str(n_inspected) + " out of "+str(len(list_of_sdists_to_inspect)) + ")")
        continue

      print(distkey + " not found in conflicts or blacklist dbs. Sending to pip.\n")

    # Else, process the dist.

    packagename = distkey[ : distkey.find('(') ]
    version_string = distkey[ distkey.find('(') + 1 : distkey.find(')')]
    assert(distkey.find(')') == len(distkey) - 1)
    formatted_requirement = packagename + "==" + version_string
    exitcode = None
    assert(CONFLICT_MODEL in [1, 2, 3])

    # Construct the argument list.
    pip_arglist = ['install', '-d', TEMPDIR_FOR_DOWNLOADED_DISTROS, DISABLE_PIP_VERSION_CHECK, '--find-dep-conflicts', str(CONFLICT_MODEL), '--conflicts-db-file', conflicts_db_fname, '--dependencies-db-file', DEPENDENCIES_DB_FILENAME]
    
    if USE_BANDERSNATCH_MIRROR:
      pip_arglist.extend(['-i', LOCATION_OF_LOCAL_INDEX_SIMPLE_LISTING])

    pip_arglist.append(formatted_requirement)

    # With arg list constructed, call pip.main with it to run a modified pip install attempt (will not install).
    # This assumes that we're dealing with my pip fork version 8.0.0.dev0seb).
    exitcode = pip.main(pip_arglist)

    # Process the output of the pip command.
    if exitcode == 2:
      print("<~> X  SDist " + distkey + " : pip errored out (code=" + str(exitcode) + "). Possible DEPENDENCY CONFLICT. Result recorded in conflicts_<...>_db.json and in conflicts_db.log. (Finished with " + str(n_inspected) + " out of " + str(len(list_of_sdists_to_inspect)) + ")")
    elif exitcode == 0:
      print("<~> .  SDist " + distkey + " : pip completed successfully. No dependency conflicts observed. (Finished with " + str(n_inspected) + " out of " + str(len(list_of_sdists_to_inspect)) + ")")
    else:
      print("<~> .  SDist " + distkey + ": pip errored out (code=" + str(exitcode) + "), but it seems to have been unrelated to any dep conflict.... (Finished with " + str(n_inspected) + " out of " + str(len(list_of_sdists_to_inspect)) + ")")
      # Store in the list of failing packages along with the python version we're running. (sys.version_info.major yields int 2 or 3)
      #   Contents are to eventually be a list of the major versions in which it fails.
      # We should never get here if the dist is already in the blacklist for this version of python, but let's keep going even if so.
      if distkey in blacklist_db and sys.version_info.major in blacklist_db[distkey] and not NO_SKIP:
        print("  WARNING! This should not happen! " + distkey + " was already in the blacklist for python " + str(sys.version_info.major) + ", thus it should not have been run unless we have --noskip on (which it is not)!")
      else: # Either the dist is not in the blacklist or it's not in the blacklist for this version of python. (Sensible)
        if distkey not in blacklist_db: # 
          blacklist_db[distkey] = [sys.version_info.major]
          print("  Added entry to blacklist for " + distkey)
        else:
          assert(NO_SKIP or sys.version_info.major not in blacklist_db[distkey])
          blacklist_db[distkey].append(sys.version_info.major)
          print("  Added additional entry to blacklist for " + distkey)

        n_added_to_blacklist += 1
        # Occasionally write the blacklist to file so we don't lose tons of blacklist info if the script
        #   has to be killed.
        if n_added_to_blacklist % 10 == 0:
          write_blacklist_to_file(blacklist_db)
          
    # end of exit code processing
    n_inspected += 1

  # end of for each tarfile/sdist

  # We're done with all packages. Write the collected blacklist back to file.
  write_blacklist_to_file(blacklist_db)


# <~> Dump the blacklist json info to file.
def write_blacklist_to_file(blacklist_db):
  with open(BLACKLIST_DB_FILENAME, 'w') as fobj:
    json.dump(blacklist_db, fobj)
  

# Given a full filename of an sdist (of the form /srv/.../packagename/packagename-1.0.0.tar.gz),
#       return package name and version (e.g. packagename-1.0.0)
# Updating to use lower().
def get_package_and_version_string_from_full_filename(fname_full):
  #     get position of last / in full filename
  i_of_last_slash = fname_full.rfind('/')
  #     get position of .tar.gz in full filename
  i_of_targz = fname_full.rfind('.tar.gz')
  return fname_full[i_of_last_slash + 1 : i_of_targz].lower()



# Given a .tar.gz in a bandersnatch mirror, determine the package name.
#     Bing's code sees fit to assume that the parent directory name is the package name.
#     I'll go with that assumption. (It breaks sometimes with dash/underscore switching,
#       but we fix that manually.)
# Updating to use lower()
def get_package_name_given_full_filename(fname_full):
  return get_parent_dir_name_from_full_path(fname_full).lower()



# Given a fully specified filename (i.e. including its path), extract name of parent directory (without full path).
def get_parent_dir_name_from_full_path(fname_full):
  #     get position of last / in full filename
  i_of_last_slash = fname_full.rfind('/')
  #     get position of 2nd to last / in full filename
  i_of_second_to_last_slash = fname_full[: i_of_last_slash].rfind('/')
  parent_dir = fname_full[i_of_second_to_last_slash + 1 : i_of_last_slash]

  return parent_dir



# Returns true if the filename given is deemed that of an sdist file, false otherwise.
def is_sdist(fname):
  return fname.endswith(SDIST_FILE_EXTENSION)


# Load given filename as a json file. If it's invalid or doesn't exist, load an empty dict.
# Give the user a chance to control-c if file contents are invalid (not if file doesn't
#   exist) by prompting for enter.
def load_json_db(filename):
  # Fill with JSON data from file.
  db = None
  fobj = None
  try:
    fobj = open(filename, "r")
    db = json.load(fobj)
  except IOError:
    print("  Directed to load " + filename + " but UNABLE TO OPEN file. Loading an empty dict.")
    db = dict()
  except (ValueError):
    fobj.close()
    print("  Directed to load " + filename + " but UNABLE TO PARSE JSON DATA from that file. Will load an empty dict.")
    input("  PRESS ENTER TO CONTINUE, CONTROL-C TO KILL AND AVOID POTENTIALLY OVERWRITING SALVAGEABLE DATA.")
    db = dict() # If it was invalid or the file didn't exist, load empty.
  return db




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
    #  # About 1% of my sample set has versions ending in "dev" that are then treated as "dev0" by pip.
    #  if deduced_version_string.endswith('dev)'): # Example: acted.projects(0.10.dev) is treated as acted.projects(0.10.dev0)
    #    deduced_version_string += "0"
    #  elif '-beta' in deduced_version_string: # Example: 2.0-beta5 is reported as 2.0b5 in the case of archgenxml
    #    deduced_version_string = deduced_version_string.replace('-beta','b')
def normalize_version_string(version):
  
  # Example: about(0.1.0-alpha.1) is reported as about(0.1.0a1) Dash removed, alpha to a, period after removed.    
  
  # 'dev' should always be preceded by a '.', not a '-'
  if '-dev' in version:
    version = version.replace('-dev', '.dev')
  elif '.dev' in version:
    pass
  elif 'dev' in version:
    version = version.replace('dev', '.dev')

  # 'dev' should not be followed by a '-'.
  if 'dev-' in version:  # Example: abl.util-0.1.5dev-20111031 is treated as abl.util(0.1.5.dev20111031), the dash removed and a '.' before dev.
    version = version.replace('dev-', 'dev')


    # Remove preceding - or . from beta or alpha.
  if '-beta' in version:  # Example: 2.0-beta5 is reported as 2.0b5 in the case of archgenxml
    version = version.replace('-beta', 'beta')
  if '.beta' in version:  # Example: 2.0-beta5 is reported as 2.0b5 in the case of archgenxml
    version = version.replace('.beta', 'beta')
  if '-alpha' in version: # Example: about(0.1.0-alpha.1) is reported as about(0.1.0a1) Dash removed, alpha to a, period after removed.
    version = version.replace('-alpha', 'alpha')
  if '.alpha' in version: # Example: 'adpy(0.12.alpha0)' is treated as 'adpy(0.12a0)'
    version = version.replace('.alpha', 'alpha')

  # Remove . or ' following alpha or beta. Example: about(0.1.0-alpha.1) is treated as about(0.1.0a1) by pip.
  if 'alpha.' in version:
    version = version.replace('alpha.', 'alpha')
  if 'alpha-' in version:
    version = version.replace('alpha-', 'alpha')
  if 'beta.' in version:
    version = version.replace('beta.', 'beta')
  if 'alpha-' in version:
    version = version.replace('beta-', 'beta')


  if version.endswith('dev') or version.endswith('beta') or version.endswith('alpha'): # beta or alpha should always be followed by a number. pip defaults to 0 in this case.
    # Example: acted.projects(0.10.dev) is treated as acted.projects(0.10.dev0)
    version += "0"


  # beta and alpha should be b and a
  # Doing this at the end may cause us to miss some cases in which (e.g.) version strings already had a in place of alpha,
  #   but it also avoids us messing up any hex strings with 'a's or 'b's in them NOT representing alpha or beta....
  # For example, if the version string is '1.2a', code above will not have correctly turned it into '1.2a0', unfortunately.
  # But then we won't mess with a version string (e.g. with commit hash in it) ending with 'a351b8a' by incorrectly adding a 0 to it.
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



  

if __name__ == "__main__":
  main()


