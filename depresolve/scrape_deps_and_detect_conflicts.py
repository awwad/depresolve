"""
<Program Name>
  scrape_deps_and_detect_conflicts.py

<Purpose>
  Employs custom version of pip (awwad/pip:develop) to harvest dependencies
  and find dependency conflicts for packages in PyPI.
  See README.md!
"""

import sys # for arguments and exceptions
import pip # for SpecifierSet, Version, and pip itself.
import os
import json
## for use in version parsing
#from distutils.version import StrictVersion, LooseVersion 

import depresolve # for logging
logger = depresolve.logging.getLogger('depresolve')

# Globals for modified pip code to use.
import depresolve.depdata as depdata
import depresolve._external.timeout as timeout # to prevent endless pip calls


# Local resources
BANDERSNATCH_MIRROR_SDIST_DIR = '/srv/pypi/web/packages/source/'
BANDERSNATCH_NEW_MIRROR_SDIST_DIR = '/srv/pypi/web/packages/'
BANDERSNATCH_MIRROR_INDEX_DIR = 'file:///srv/pypi/web/simple'
WORKING_DIRECTORY = os.path.join(os.getcwd()) #'/Users/s/w/git/pypi-depresolve' in my setup
TEMPDIR_FOR_DOWNLOADED_DISTROS = os.path.join(WORKING_DIRECTORY,
  'temp_distros')

# Other Assumptions
# assume the archived packages bandersnatch grabs end in this:
SDIST_FILE_EXTENSION = '.tar.gz'




# Argument handling:
#
#    ANY ARGS NOT MATCHING the patterns below are interpreted as what I will
#    refer to as 'distkeys':
#      packagename(packageversion)
#      e.g.:   "django(1.8)"
#      Your shell will presumably want these the distkeys passed in quotes
#      because of the parentheses.
#
#  DEPENDENCY CONFLICT MODELS (see README)
#   --cm1  use conflict model 1: all resolvable & unresolvable conflicts
#   --cm2  use conflict model 2: all unresolvable and some resolvable conflicts
#   --cm3  use conflict model 3: default; basically "would pip get this right?"
#
#  GENERAL ARGUMENTS:
#   --noskip Don't skip packages in the blacklist or packages for which
#            information on whether or not a conflict occurs is already stored.
#   --carefulskip  Don't skip packages if we don't have dependency info for
#                  them, even if they're in the blacklist or we already have
#                  conflict info.
#
#  REMOTE OPERATION:   (DEFAULT!)
#    Not using --local means we're downloading from PyPI, per pip's defaults.
#
#
#  LOCAL OPERATION: For use when operating with local sdist files
#                   (e.g. with a bandersnatched local PyPI mirror)
#
#   --local-old Instead of fetching packages from PyPI normally via pip,
#            instruct pip to use a local mirror index on this machine, with
#            address equal to BANDERSNATCH_MIRROR_INDEX_DIR.
#            This is used with pip's '-i' argument.
#            It is assumed that the mirror directory structure is consistent
#            with versions of bandersnatch <=1.8. Newer versions of
#            bandersnatch will store source distribution files differently,
#            and if you created your mirror with a newer version of
#            bandersnatch, you should use --local instead of --local-old.
#
#            If you use --local-old and specify no distkeys to scrape, they
#            will be chosen alphabetically from the local mirror index until we
#            we have the number specified by the --n argument below.
#
#   --local  As with --local-old, but expecting the directory structure created
#            by bandersnatch version 1.11 (not sure what the cutoff version is)
#            
#            If you use --local and specify no distkeys to scrape, they will be
#            chosen in some arbitrary order, all distributions of one package
#            consecutively, one package at a time, until we have the number
#            specified by the --n argument below.
#   
#   --n=N    For use only with --local and --local-old.
#            Sets N as the max packages to inspect when pulling from local PyPI
#            mirror.
#            e.g. --n=1  or  --n=10000
#            Default for --local* runs, if this arg is not specified, is all
#            packages in the entire local PyPI mirror at /srv/pypi)
#
#
#   EXAMPLE CALLS:
#
#    ~~ Run on a single package (in this case, arnold version 0.3.0) pulled
#       from remote PyPI, using conflict model 3 (default):
#
#       >  python scrape_deps_and_detect_conflicts.py 'arnold(0.3.0)'
#
#
#    ~~ Run on a few packages from PyPI, using conflict model 2, and without
#       skipping even if conflict info on those packages is already
#       available, or if they're in the blacklist for having hit unexpected
#       errors in previous runs:
#
#       >  python scrape_deps_and_detect_conflicts.py 'motorengine(0.7.4)' 'django(1.6.3)' --cm2 --noskip
#
#
#    ~~ Run on the first 10 packages in the local pypi mirror
#       (assumed /srv/pypi) alphabetically, using conflict model 1.
#
#       >  python scrape_deps_and_detect_conflicts.py --cm1 --local --n=10
#
#
#    ~~ Run on django(1.8.3), but use the local mirror to retrieve packages.
#
#       > python scrape_deps_and_detect_conflicts.py --local 'django(1.8.3)'
#
#

def main():
  # Some defaults:
  n_sdists_to_process = 0 # debug; max packages to explore during debug - overriden by --n=N argument.
  conflict_model = 3
  no_skip = False
  careful_skip = False
  use_local_index = False
  use_local_index_old = False
  #run_all_conflicting = False

  # Files and directories.
  assert(os.path.exists(WORKING_DIRECTORY)), 'Working dir does not exist...??'

  # Ensure that appropriate directory for downloaded distros exists.
  # This would be terrible to duplicate if scraping a large number of packages.
  # One such sdist cache per system! Gets big.
  if not os.path.exists(TEMPDIR_FOR_DOWNLOADED_DISTROS):
    os.makedirs(TEMPDIR_FOR_DOWNLOADED_DISTROS)



  logger.info("scrape_deps_and_detect_conflicts - Version 0.5")
  distkeys_to_inspect_not_normalized = [] # not-yet-normalized user input, potentially filled with distkeys to check, from arguments
  distkeys_to_inspect = [] # list after argument normalization

  # Argument processing.
  # If we have arguments coming in, treat those as the packages to inspect.
  if len(sys.argv) > 1:
    for arg in sys.argv[1:]:
      if arg.startswith("--n="):
        n_sdists_to_process = int(arg[4:])
      elif arg == "--cm1":
        conflict_model = 1
      elif arg == "--cm2":
        conflict_model = 2
      elif arg == "--cm3":
        conflict_model = 3
      elif arg == "--noskip":
        no_skip = True
      elif arg == '--carefulskip':
        careful_skip = True
      elif arg == "--local-old":
        # without ='<directory>' means we pull alphabetically from local PyPI
        # mirror at /srv/pypi/
        # Parse .tar.gz files as they appear in bandersnatch version <= 1.8
        # For newer versions of bandersnatch, the sdist files are stored
        # differently (not in project-based directories) and so the argument
        # --local should be used instead.
        use_local_index_old = True
      elif arg == "--local":
        # without ='<directory>' means we pull from local PyPI mirror at
        # /srv/pypi/
        # Parse .tar.gz files as they appear in bandersnatch version 1.11
        # For bandersnatch 1.11, the sdist files are stored differently than in
        # <1.8. They are no longer kept in project-based directories).
        # If you are using a version of bandersnatch <=1.8, the argument
        # --local-old should be used instead.
        use_local_index = True
      #elif arg == '--conflicting':
      #  # Operate locally and run on the distkeys provided in the indicated
      #  # file, each on its own line.
      #  use_local_index = True
      #  run_all_conflicting = True
      else:
        distkeys_to_inspect_not_normalized.append(arg) # e.g. 'motorengine(0.7.4)'
        # For simplicity right now, I'll use one mode or another, not both.
        # Last arg has it if both.


  # Normalize any input distkeys we were given.
  for distkey in distkeys_to_inspect_not_normalized:
    assert '(' in distkey and distkey.endswith(')'), 'Invalid input.'
    distkey = depdata.normalize_distkey(distkey)
    distkeys_to_inspect.append(distkey)


  # Were we not given any distkeys to inspect?
  if not distkeys_to_inspect:# and not run_all_conflicting:

    if not use_local_index and not use_local_index_old:
      # If we're not using a local index, we have nothing to do.
      raise ValueError('You neither specified distributions to scrape nor '
          '(alternatively) indicated that they should be chosen from a local '
          'mirror.')

    elif use_local_index_old:
      # If we were told to work with a local mirror, but weren't given specific
      # sdists to inspect, we'll scan everything in
      # BANDERSNATCH_MIRROR_SDIST_DIR until we have n_sdists_to_process sdists.
      # There is a better way to do this, but I'll leave this as is for now.

      # Ensure that the local PyPI mirror directory exists first.
      if not os.path.exists(BANDERSNATCH_MIRROR_SDIST_DIR):
        raise Exception('--- Exception. Expecting a bandersnatched mirror of '
            'PyPI at ' + BANDERSNATCH_MIRROR_SDIST_DIR + ' but that directory '
            'does not exist.')
      i = 0
      for dir, subdirs, files in os.walk(BANDERSNATCH_MIRROR_SDIST_DIR):
        for fname in files:
          if is_sdist(fname):
            tarfilename_full = os.path.join(dir, fname)
            # Deduce package names and versions from sdist filename.
            distkey = get_distkey_from_full_filename(tarfilename_full)
            distkeys_to_inspect.append(distkey)
            i += 1
            # awkward control structures, but saving debug run time. tidy later
            if i >= n_sdists_to_process:
              break
        if i >= n_sdists_to_process:
          break

    else: # use_local_index (modern bandersnatch version)
      assert use_local_index, 'Programming error.'
      # # sdists live here: /srv/pypi/web/packages/??/??/*/*.tar.gz
      # # Can implement this such that it checks those places.
      # for name1 in os.listdir(BANDERSNATCH_NEW_MIRROR_SDIST_DIR):
      #   if len(name1) != 2:
      #     continue
      #   for name2 in os.listdir(os.path.join(
      #       BANDERSNATCH_NEW_MIRROR_SDIST_DIR, name1)):
      #     if len(name2) != 2:
      #       continue
      #     for name3 in os.listdir(os.path.join(
      #         BANDERSNATCH_NEW_MIRROR_SDIST_DIR, name1, name2)):
      #       if len(name3) != 60:
      #         continue
      #       for fname in os.listdir():
      #  #.... No, this is not going to unambiguously get me the package name
      #  # in the way that it used to in older versions of bandersnatch.
      #  # Rather than dealing with unexpected naming consequences, I'll go
      #  # with the following even more annoying hack....

      # A dictionary of all versions of all packages on the mirror,
      # collected out-of-band (via xml-rpc at same time as mirroring occurred).
      vbp_mirror = json.load(open('data/versions_by_package.json', 'r'))
      i = 0
      for package in vbp_mirror:
        if i >= n_sdists_to_process:
          break

        for version in vbp_mirror[package]:

          if i >= n_sdists_to_process:
            break

          distkey = depdata.distkey_format(package, version)
          distkeys_to_inspect.append(distkey)

          i += 1



  # We should now have distkeys to inspect (unless run_all_conflicting is True).


  # Load the dependencies, conflicts, and blacklist databases.
  # The blacklist is a list of runs that resulted in errors or runs that were
  # manually added because, for example, they hang seemingly forever or take an
  # inordinate length of time.
  depdata.ensure_data_loaded([conflict_model])

  # Alias depdata.conflicts_db to the relevant conflicts db. (Ugly)
  depdata.set_conflict_model_legacy(conflict_model) # should remove this


  #if run_all_conflicting:
  #  distkeys_to_inspect = [distkey for distkey in depdata.conflicts_3_db if
  #      depdata.conflicts_3_db[distkey]]


  n_inspected = 0
  n_successfully_processed = 0
  last_wrote_at = 0

  # Now take all of the distkeys ( e.g. 'python-twitter(0.2.1)' ) indicated and
  # run on them.
  for distkey in distkeys_to_inspect:
    
    # To avoid losing too much data, make sure we at least write data to disk
    # about every 100 successfully processed or 10000 inspected dists. Avoid
    # writing repeatedly in edge cases (e.g. when we write after 100
    # successfully processed and then have to keep writing for every skip that
    # occurs after that.
    progress = n_inspected + n_successfully_processed * 100
    if progress > last_wrote_at + 10000:
      last_wrote_at = progress
      logger.info("Writing early.")
      depdata.write_data_to_files([conflict_model])


    # The skip conditions.

    # If dist is in the blacklist for the same version of python we're running.
    blacklisted = distkey in depdata.blacklist \
        and sys.version_info.major in depdata.blacklist[distkey]

    # If dist has conflict info saved already
    already_in_conflicts = distkey in depdata.conflicts_db

    # Do we have dep info for the dist? Not a skip condition, but part of
    # careful_skip tests.
    already_in_dependencies = distkey in depdata.dependencies_by_dist


    # If we're not in no_skip mode, perform the skip checks.
    # Skip checks. If the dist is blacklisted or we already have dependency
    # data, then skip it - unless we're in careful skip mode and we don't
    # have dependency data for the dist.
    if not no_skip and (blacklisted or already_in_conflicts):

      # If dist isn't blacklisted, we already have conflict info, there's no
      # dependency info, and careful skip is on, don't actually skip.
      if careful_skip and not already_in_dependencies and not blacklisted:
        print('---    Not skipping ' + distkey + ': ' +
            'Already have conflict data, however there is no dependency info '
            'for the dist, the dist is not blacklisted, and we are in '
            'careful_skip mode.')

      else: # Skip, since we don't have a reason not to.
        n_inspected += 1
        print('---    SKIP -- ' + distkey + ': ' +
            'Blacklisted. '*blacklisted +
            'Already have conflict data. '*already_in_conflicts +
            '(Finished ' + str(n_inspected) + ' out of ' +
            str(len(distkeys_to_inspect)) + ')')
        continue


    # If we didn't skip, process the dist.

    packagename = depdata.get_packname(distkey)
    version_string = depdata.get_version(distkey)
    #assert(distkey.rfind(')') == len(distkey) - 1)
    formatted_requirement = packagename + "==" + version_string
    exitcode = None
    assert(conflict_model in [1, 2, 3])

    # Construct the argument list.
    # Include argument to pass to pip to tell it not to prod users about our
    # strange pip version (lest they follow that instruction and install a
    # standard pip version):
    pip_arglist = [
      'install',
      '-d', TEMPDIR_FOR_DOWNLOADED_DISTROS,
      '--disable-pip-version-check',
      '--find-dep-conflicts', str(conflict_model),
      '--quiet']
    
    if use_local_index:
      pip_arglist.extend(['-i', BANDERSNATCH_MIRROR_INDEX_DIR])

    pip_arglist.append(formatted_requirement)

    # With arg list constructed, call pip.main with it to run a modified pip
    # install attempt (will not install).
    # This assumes that we're dealing with my pip fork version 8.0.0.dev0seb).
    print('---    Sending ' + distkey + ' to pip.')
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
      print('--- X  SDist ' + distkey + ' : pip errored out (code=' +
        str(exitcode) + '). Possible DEPENDENCY CONFLICT. Result recorded in '
        'conflicts_<...>.json. (Finished ' +
        str(n_inspected) + ' out of ' + str(len(distkeys_to_inspect)) +
        ')')
    elif exitcode == 0:
      print('--- .  SDist ' + distkey + ' : pip completed successfully. '
        'No dependency conflicts observed. (Finished ' + str(n_inspected)
        + ' out of ' + str(len(distkeys_to_inspect)) + ')')
    else:
      print('--- .  SDist ' + distkey + ': pip errored out (code=' +
        str(exitcode) + '), but it seems to have been unrelated to any dep '
        'conflict.... (Finished ' + str(n_inspected) + ' out of ' +
        str(len(distkeys_to_inspect)) + ')')
      # Store in the list of failing packages along with the python version
      # we're running. (sys.version_info.major yields int 2 or 3)
      # Contents are to eventually be a list of the major versions in which it
      # fails. We should never get here if the dist is already in the blacklist
      # for this version of python, but let's keep going even if so.
      if distkey in depdata.blacklist and sys.version_info.major in \
        depdata.blacklist[distkey] and not no_skip:
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
          assert(no_skip or sys.version_info.major not in depdata.blacklist[distkey])
          depdata.blacklist[distkey].append(sys.version_info.major)
          logger.info("  Added additional entry to blacklist for " + distkey)

          
    # end of exit code processing
    n_inspected += 1
    n_successfully_processed += 1

  # end of for each tarfile/sdist

  # We're done with all packages. Write the collected data back to file.
  logger.debug("Writing.")
  depdata.write_data_to_files([conflict_model])





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

  packname = depdata.normalize_package_name(unnormalized_packagename)
  version = depdata.normalize_version_string(unnormalized_version)

  distkey = depdata.distkey_format(packname, version)

  return distkey





if __name__ == "__main__":
  main()
