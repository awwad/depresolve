"""
<Program Name>
  scrape_deps_and_detect_conflicts.py

<Purpose>
  Employs custom version of pip (awwad/pip:develop) to harvest dependencies
  and find dependency conflicts for packages in PyPI.
  See README.md!
"""

import sys # for arguments and exceptions
import pip # for SpecifierSet and Version (TODO: Refine.)
import os
import json
## for use in version parsing
#from distutils.version import StrictVersion, LooseVersion 

import depresolve # for logging

# Globals for modified pip code to use.
# These have to be before the imports below, to avoid circular issues.
import depresolve.depdata as depdata
import depresolve._external.timeout as timeout # to prevent endless pip calls

from depresolve.depdata import get_version, get_packname
from depresolve.depdata import distkey_format, get_pack_and_version


# Local resources
BANDERSNATCH_MIRROR_DIR = '/srv/pypi/web/packages/source/'
LOCATION_OF_LOCAL_INDEX_SIMPLE_LISTING = 'file:///srv/pypi/web/simple'
WORKING_DIRECTORY = os.path.join(os.getcwd()) #'/Users/s/w/git/pypi-depresolve' in my setup
TEMPDIR_FOR_DOWNLOADED_DISTROS = os.path.join(WORKING_DIRECTORY,
  'temp_distros')

# Other Assumptions
# assume the archived packages bandersnatch grabs end in this:
SDIST_FILE_EXTENSION = '.tar.gz'




# Argument handling:
#  DEPENDENCY CONFLICT MODELS (see README)
#   --cm1  use conflict model 1: all resolvable & unresolvable conflicts
#   --cm2  use conflict model 2: all unresolvable and some resolvable conflicts
#   --cm3  use conflict model 3: default; basically "would pip get this right?"
#
#  GENERAL ARGUMENTS:
#   --noskip Don't skip packages in the blacklist or packages for which
#            information on whether or not a conflict occurs is already stored.
#
#  REMOTE OPERATION:   (DEFAULT!)
#    ANY ARGS NOT MATCHING the other patterns are interpreted as what I will
#    refer to as 'distkeys':
#    packagename(packageversion)
#    e.g.:   "django(1.8)"
#    Using one of these means we're downloading from PyPI, per pip's defaults.
#    Your shell will presumably want these arguments passed in quotes because
#    of the parentheses.
#
#
#  LOCAL OPERATION: For use when operating with local sdist files
#                   (e.g. with a bandersnatched local PyPI mirror)
#   --local=FNAME  specifies a local .tar.gz sdist to inspect for dependency
#                  conflicts with pip for dependency conflicts
#                  e.g. '--local=/srv/pypi/web/packages/source/M/motorengine/motorengine-0.7.4.tar.gz'
#                  You can specify as many of these as you like with separate
#                  --local=<file> arguments.
#                  Local and remote execution are mutually exclusive.
#
#   --local  Using this without "=<file.tar.gz>" means we should alphabetically
#            scan from the local PyPI mirror. This is mutually exclusive with
#            the --local=<fname> usage above. If files are specified, we only
#            check the files specified.
#   
#   --n=N    For use only with --local (not remotes, not --local=<file>).
#            Sets N as the max packages to inspect when pulling alphabetically
#            from local PyPI mirror.
#            e.g. --n=1  or  --n=10000
#            Default for --local runs, if this arg is not specified, is all
#            packages in the entire local PyPI mirror at /srv/pypi)
#            (TODO: Must confirm that using this arg won't impact remote
#            operation, just for cleanliness.)
#
#
#
#   EXAMPLE CALLS:
#
#    ~~ Run on a single package (in this case, arnold version 0.3.0) pulled
#       from remote PyPI, using conflict model 3 (default):
#
#       >  python scrape_deps_and_detect_conflicts.py "arnold(0.3.0)"
#
#
#    ~~ Run on a few packages from PyPI, using conflict model 2, and without
#       skipping even if conflict info on those packages is already
#       available, or if they're in the blacklist for having hit unexpected
#       errors in previous runs:
#
#       >  python scrape_deps_and_detect_conflicts.py "motorengine(0.7.4)" "django(1.6.3)" --cm2 --noskip
#
#
#    ~~ Run on a single specified package, motorengine 0.7.4, stored locally,
#       using conflict model 2:
#           
#       >  python scrape_deps_and_detect_conflicts.py --cm2 --local=/srv/pypi/web/packages/source/M/motorengine/motorengine-0.7.4.tar.gz
#
#    ~~ Run on the first 10 packages in the local pypi mirror
#       (assumed /srv/pypi) alphabetically, using conflict model 1.
#
#       >  python scrape_deps_and_detect_conflicts.py --cm1 --local --n=10
#
def main():
  # Some defaults:
  DEBUG__N_SDISTS_TO_PROCESS = 0 # debug; max packages to explore during debug - overriden by --n=N argument.
  CONFLICT_MODEL = 3
  NO_SKIP = False
  USE_BANDERSNATCH_MIRROR = False


  # Files and directories.
  assert(os.path.exists(WORKING_DIRECTORY)), 'Working dir does not exist...??'


  logger = depresolve.logging.getLogger('scrape_deps_and_detect_conflicts')

  # Ensure that appropriate directory for downloaded distros exists.
  # This would be terrible to duplicate if scraping a large number of packages.
  # One such sdist cache per system! Gets big.
  if not os.path.exists(TEMPDIR_FOR_DOWNLOADED_DISTROS):
    os.makedirs(TEMPDIR_FOR_DOWNLOADED_DISTROS)



  logger.info("scrape_deps_and_detect_conflicts - Version 0.4")
  list_of_sdists_to_inspect = [] # potentially filled with local sdist filenames, from arguments
  list_of_remotes_to_inspect = [] # potentially filled with remote packages to check, from arguments

  # Argument processing.
  # If we have arguments coming in, treat those as the packages to inspect.
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
      elif arg == "--local":
      # without ='<some file>' means we pull alphabetically from local PyPI mirror at /srv/pypi/
        USE_BANDERSNATCH_MIRROR = True
      elif arg.startswith("--local="):
        list_of_sdists_to_inspect.append(arg[8:])
        # e.g. '--local=/srv/pypi/web/packages/source/M/motorengine/motorengine-0.7.4.tar.gz'
        USE_BANDERSNATCH_MIRROR = True
      else:
        list_of_remotes_to_inspect.append(arg) # e.g. 'motorengine(0.7.4)'
        # For simplicity right now, I'll use one mode or another, not both.
        # Last arg has it if both.
        USE_BANDERSNATCH_MIRROR = False

  # If we were told to work with a local mirror, but weren't given specific
  # sdists to inspect, we'll scan everything in BANDERSNATCH_MIRROR_DIR until
  # we have DEBUG__N_SDISTS_TO_PROCESS sdists.
  if USE_BANDERSNATCH_MIRROR and not list_of_sdists_to_inspect:
    # Ensure that the local PyPI mirror directory exists first.
    if not os.path.exists(BANDERSNATCH_MIRROR_DIR):
      raise Exception('--- Exception. Expecting a bandersnatched mirror of '
          'PyPI at ' + BANDERSNATCH_MIRROR_DIR + ' but that directory does not'
          ' exist.')
    i = 0
    for dir, subdirs, files in os.walk(BANDERSNATCH_MIRROR_DIR):
      for fname in files:
        if is_sdist(fname):
          list_of_sdists_to_inspect.append(os.path.join(dir, fname))
          i += 1
          # awkward control structures, but saving debug run time. tidy later.
          if i >= DEBUG__N_SDISTS_TO_PROCESS:
            break
      if i >= DEBUG__N_SDISTS_TO_PROCESS:
        break


  # Load the dependencies, conflicts, and blacklist databases.
  # The blacklist is a list of runs that resulted in errors or runs that were
  # manually added because, for example, they hang seemingly forever or take an
  # inordinate length of time.
  depdata.ensure_data_loaded([CONFLICT_MODEL])

  # Alias depdata.conflicts_db to the relevant conflicts db. (Ugly)
  depdata.set_conflict_model_legacy(CONFLICT_MODEL)


  # Probably not necessary anymore. Verify and remove. TODO.
  # For backward compatibility (before casing fixes for certain package names):
  #   Determine a lower-cased set of the keys in the conflicts db.
  keys_in_conflicts_db_lower = set(k.lower() for k in depdata.conflicts_db)



  n_inspected = 0
  n_successfully_processed = 0

  # Generate a list of distkeys (e.g. 'django(1.8.3)') to inspect, from the
  # lists of sdists and "remotes".
  distkeys_to_inspect = []
  if USE_BANDERSNATCH_MIRROR:
    for tarfilename_full in list_of_sdists_to_inspect:
      # Deduce package names and versions from sdist filename.
      distkey = get_distkey_from_full_filename(tarfilename_full)
      distkeys_to_inspect.append(distkey)
      
  else: # if not using local bandersnatched PyPI mirror
    for distkey in list_of_remotes_to_inspect:
      assert '(' in distkey and distkey.endswith(')'), "Invalid input."
      distkey = normalize_distkey(distkey)
      distkeys_to_inspect.append(distkey)
    

  # Now take all of the distkeys ( e.g. 'python-twitter(0.2.1)' ) indicated and
  # run on them.
  for distkey in distkeys_to_inspect:
    
    # To avoid losing too much data, make sure we at least write data to disk
    # every 20 dists.
    if n_inspected % 10000 == 9999 or n_successfully_processed % 100 == 99:
      logger.info("Writing early.")
      depdata.write_data_to_files([CONFLICT_MODEL])


    # Check to see if we already have conflict info for this package.
    # If so, don't run for it.
    if not NO_SKIP:
      if distkey in keys_in_conflicts_db_lower:
        n_inspected += 1
        logger.info("---    SKIP -- Already have " + distkey + " in db of " +
          "type " + str(CONFLICT_MODEL) + " conflicts. Skipping. (Now at " +
          str(n_inspected) + " out of " + str(len(list_of_sdists_to_inspect)) +
          ")")
        continue

      # Else if the dist is listed in the blacklist along with this python
      # major version (2 or 3), skip.
      elif distkey in depdata.blacklist and \
        sys.version_info.major in depdata.blacklist[distkey]:
        n_inspected += 1
        logger.info("---    SKIP -- Blacklist includes " + distkey +
          ". Skipping. (Now at " + str(n_inspected) + " out of " +
          str(len(list_of_sdists_to_inspect)) + ")")
        continue

      logger.debug(distkey + ' not found in conflicts or blacklist dbs. '
        'Sending to pip.\n')

    # Else, process the dist.

    packagename = get_packname(distkey)
    version_string = get_version(distkey)
    #assert(distkey.rfind(')') == len(distkey) - 1)
    formatted_requirement = packagename + "==" + version_string
    exitcode = None
    assert(CONFLICT_MODEL in [1, 2, 3])

    # Construct the argument list.
    # Include argument to pass to pip to tell it not to prod users about our
    # strange pip version (lest they follow that instruction and install a
    # standard pip version):
    pip_arglist = [
      'install',
      '-d', TEMPDIR_FOR_DOWNLOADED_DISTROS,
      '--disable-pip-version-check',
      '--find-dep-conflicts', str(CONFLICT_MODEL),
      '--quiet']
    
    if USE_BANDERSNATCH_MIRROR:
      pip_arglist.extend(['-i', LOCATION_OF_LOCAL_INDEX_SIMPLE_LISTING])

    pip_arglist.append(formatted_requirement)

    # With arg list constructed, call pip.main with it to run a modified pip
    # install attempt (will not install).
    # This assumes that we're dealing with my pip fork version 8.0.0.dev0seb).
    logger.debug('Scraper says: before pip call, len(deps) is ' +
        str(len(depdata.dependencies_by_dist)))

    # Call pip, with a 5 minute timeout.
    exitcode = None # scoping paranoia
    try:
      exitcode = _call_pip_with_timeout(pip_arglist)
    except timeout.TimeoutException as e: # This catch is not likely. See below
      logger.warning('pip timed out on dist ' + distkey + '(5min)!'
          ' Will treat as error. Exception follows: ' + str(e.args))
      # Set the exit code to something other than 2 or 0 and it'll be treated
      # like any old pip error below, resulting in a blacklist.
      exitcode = 1000

    # However, unfortunately, we cannot assume that pip will let that exception
    # pass up to us. It seems to take the signal, stop and clean up, and then
    # return exit code 2. This is fine, except that then we can't really
    # blacklist the process. I'd have to add a timer here, detect something
    # very close to the timeout, and guess that it timed out. /: That sucks.
    # In any case, we'll not learn that it's a process that times out, but
    # we'll just look at it as a possible conflict case. (The data recorded
    # will not list it as a conflict. Hopefully, that data is not corrupted.
    # It's unlikely that it would have been, though, so I judge this OK.)
    
    # Process the output of the pip command.
    if exitcode == 2:
      logger.info("--- X  SDist " + distkey + " : pip errored out (code=" +
        str(exitcode) + "). Possible DEPENDENCY CONFLICT. Result recorded in "
        "conflicts_<...>.json. (Finished with " +
        str(n_inspected) + " out of " + str(len(list_of_sdists_to_inspect)) +
        ")")
    elif exitcode == 0:
      logger.info("--- .  SDist " + distkey + " : pip completed successfully. "
        "No dependency conflicts observed. (Finished with " + str(n_inspected)
        + " out of " + str(len(list_of_sdists_to_inspect)) + ")")
    else:
      logger.debug("--- .  SDist " + distkey + ": pip errored out (code=" +
        str(exitcode) + "), but it seems to have been unrelated to any dep "
        "conflict.... (Finished with " + str(n_inspected) + " out of " +
        str(len(list_of_sdists_to_inspect)) + ")")
      # Store in the list of failing packages along with the python version
      # we're running. (sys.version_info.major yields int 2 or 3)
      # Contents are to eventually be a list of the major versions in which it
      # fails. We should never get here if the dist is already in the blacklist
      # for this version of python, but let's keep going even if so.
      if distkey in depdata.blacklist and sys.version_info.major in \
        depdata.blacklist[distkey] and not NO_SKIP:
        logger.warning('  WARNING! This should not happen! ' + distkey + ' was'
          'already in the blacklist for python ' + str(sys.version_info.major)
          + ', thus it should not have been run unless we have --noskip on '
          '(which it is not)!')
      else:
      # Either the dist is not in the blacklist or it's not in the blacklist
      # for this version of python. (Sensible)
        if distkey not in depdata.blacklist: # 
          depdata.blacklist[distkey] = [sys.version_info.major]
          logger.info("  Added entry to blacklist for " + distkey)
        else:
          assert(NO_SKIP or sys.version_info.major not in depdata.blacklist[distkey])
          depdata.blacklist[distkey].append(sys.version_info.major)
          logger.info("  Added additional entry to blacklist for " + distkey)

          
    # end of exit code processing
    n_inspected += 1
    n_successfully_processed += 1

  # end of for each tarfile/sdist

  # We're done with all packages. Write the collected data back to file.
  logger.debug("Writing.")
  depdata.write_data_to_files([CONFLICT_MODEL])





@timeout.timeout(300) # Timeout after 5 minutes.
def _call_pip_with_timeout(pip_arglist):
  """
  This function exists to allow us to call pip but prevent pip from going on
  forever in case of strange behavior (like waiting for a sudo password when
  no package should need sudo to determine dependencies, etc.). In practice,
  when pip gets hit with a SIGALRM from this, it will clean up and return with
  the exitcode 2. It won't be possible to distinguish whether it timed out or
  was some other error (without some ugliness), so we make do.
  """
  exitcode = pip.main(pip_arglist)
  return exitcode





# Returns true if the filename given is deemed that of an sdist file, false
# otherwise.
def is_sdist(fname):
  return fname.endswith(SDIST_FILE_EXTENSION)





def get_distkey_from_full_filename(fname_full):
  """
  Given a full filename of an sdist (a .tar.gz in a bandersnatch mirror, say,
  of the form e.g. /srv/.../packagename/packagename-1.0.0.tar.gz), return the
  distkey, the key I use to identify the distribution, format currently
  'packname(version)'.

  Also perform some normalizations to match what we can expect from pip.
  """

  #     get position of last / in full filename
  i_of_last_slash = fname_full.rfind('/')
  #     get position of 2nd to last / in full filename
  i_of_second_to_last_slash = fname_full[: i_of_last_slash].rfind('/')
  #     get position of .tar.gz in full filename
  i_of_targz = fname_full.rfind('.tar.gz')

  # Parent directory roughly dictates the package name.
  parent_dir = fname_full[i_of_second_to_last_slash + 1 : i_of_last_slash]
  unnormalized_packagename = parent_dir

  unnormalized_package_and_version = \
      fname_full[i_of_last_slash + 1 : i_of_targz].lower()

  # Subtract the unnormalized packagename to get the unnormalized version str.
  unnormalized_version = \
      unnormalized_package_and_version[len(unnormalized_packagename) + 1 :]

  # Now normalize them both and combine them into a normalized distkey.

  packname = normalize_package_name(unnormalized_packagename)
  version = normalize_version_string(unnormalized_version)

  distkey = distkey_format(packname, version)

  return distkey





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
    normalized = normalize_version_string(version)
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





if __name__ == "__main__":
  main()
