"""
<Program Name>
  rbtpip_integrate.py

<Purpose>
  A script to test rbtcollins' backtracking resolver patch for pip, using
  some depresolve code to do analysis.
"""

import subprocess # shell commands to create and use virtual environments
import random, string # randomized naming for virtual environments
import sys # for arguments to main
import os # for directory creation
import json
import depresolve
import depresolve.depdata as depdata
import depresolve.resolver.resolvability as ry
import depresolve._external.timeout as timeout
import traceback

SOLUTIONS_JSON_FNAME = 'data/resolved_via_rbtpip.json'
VENV_CATALOG_JSON_FNAME = 'data/rbtpip_venv_catalog.json'
VENVS_DIR = 'rbt_venvs'


venv_catalog = None

class UnrelatedInstallFailure(Exception):
  pass

def rbttest(distkey, edeps, versions, local=False,
    dir_rbt_pip='../pipcollins'):
  """

  Accepts a distkey indicating what distribution to try to install using
  rbtcollins' issue-988 pip branch as a way to solve conflicts.

  Steps:
    1. Solve using rbtcollins' pip branch issue-988:
       For each distkey, create a new virtual environment, install rbtcollins'
       pip version within it, use it to install the dist indicated, and use
       `pip list` to determine what it installed.

    2. Run resolvability.are_fully_satisfied to test the solution set for
       consistency.


  Arguments:
    - distkeys: a list of distkeys indicating what distributions to solve for
    - edeps: elaborated dependency data (see depdata.py)
    - versions: versions by package (dict mapping package name to the available
      versions for that package)
    - local (optional):
        - if not provided, we connect to PyPI
        - if simply set to 'True', we use the default local bandersnatch
          location for the simple listing of packages,
          'file:///srv/pypi/web/simple'.
        - if another value is provided, we interpret it as a string indicating
          the location of the simple index listing of packages on the mirror
          to use.

  Returns:
    - Installed: True if distkey was able to be installed with rbt pip
    - Satisfied: True if the solution set rbt pip generated was fully
      satisfied, i.e. all dependencies of the given dist were satisfied, along
      with all of their dependencies, and so on, with no dependency conflicts.
    - Solution: the solution set (all distkeys installed)
    - errstring: a string describing the error encountered if any was
      encountered.
    - stderr_installation: stderr.read().decode() for the pip install
      subprocess command that installed the distribution. In case of install
      errors. Empty string if stderr was empty.

  Raises:
    - UnrelatedInstallFailure if the the installation fails in some trivial way
      that merits trying again.

  """


  logger = depresolve.logging.getLogger('rbtpip_integrate.rbttest')

  errstring = ''

  # Sanitize distkey:
  unsanitized_distkey = distkey # storing only for debug
  distkey = depdata.normalize_distkey(distkey)
  logger.debug('Sanitizing distkey: from ' + unsanitized_distkey + ' to ' +
      distkey)


  ###############
  # Step 1
  # Figure out the install candidate solution.
  logger.info('Starting rbt resolve of ' + distkey)

  # declaring here for try/except scope reasons;
  # declaring two for distkey normalization & debug
  unsanitized_solution = []
  solution = []
  stderr_installation = '' # will be whatever is printed to stderr during the
  # installation of the distribution using rbtpip

  # Run rbtcollins' pip branch to find the solution, with some acrobatics.
  try:
    (unsanitized_solution, stderr_installation) = \
        rbt_backtracking_satisfy(distkey, edeps, versions, local)

  except depresolve._external.timeout.TimeoutException as e:
    errstring = 'Timed out during install'
    logger.error('Unable to install ' + distkey + ' using rbt pip. ' +
        errstring)
    return (False, False, [], errstring, stderr_installation)

  except UnrelatedInstallFailure as e:
    # Expect this to just be retried immediately.
    raise
    #errstring = e.msg
    # Failed to get through the early stages of the install.
    #return (False, False, [], errstring, stderr_installation)

  
  # Sanitize solution, which may in particular have non-lowercase names:
  for sol_distkey in unsanitized_solution:
    solution.append(depdata.normalize_distkey(sol_distkey))



  ###############
  # Step 2: Run resolvability.are_fully_satisfied to test the solution set
  # for consistency.

  # Test the solution.
  # If the given solution doesn't even include the distribution to install
  # itself, it's obviously not been successful.

  satisfied = False
  installed = distkey in [d.lower() for d in solution] # sanitize old data

  if not installed:

    if 'Hit step limit during requirement resolving.' in stderr_installation:
      errstring = 'Hit step limit during requirement resolving.'
      logger.error('Unable to install ' + distkey + ' using rbt pip. ' +
          errstring + '. Solution does not contain ' + distkey + '. Solution '
          'was: ' + str(solution))


    elif 'Timed out' in stderr_installation:
      errstring = 'Timed out: >5min install'
      logger.error('Unable to install ' + distkey + ' using rbt pip. ' +
          errstring + '. Solution does not contain ' + distkey + '. Solution '
          'was: ' + str(solution))


    elif solution:
      errstring = 'Non-empty solution without target distkey'
      logger.error('Unable to install ' + distkey + ' using rbt pip. ' + 
          errstring + '. Solution does not contain ' + distkey + '. Presume '
          'failure; unclear why anything was installed at all - possibly '
          'failure in middle of installations, after some dependencies were '
          'installed? Solution was: ' + str(solution))
    
    else:
      errstring = 'Empty solution, reason unknown.'
      logger.error('Unable to install ' + distkey + ' using rbt pip. ' +
          errstring + '. Presume pip failure.')

  else:
    # If it's in there, then we check to see if the solution is fully
    # satisfied. (Note that because virtual environments start off with pip,
    # wheel, and setuptools, we can't tell when a solution includes them,
    # don't store those as part of the solution, and so disregard them in this
    # dependency check. ):
    try:
      satisfied = ry.are_fully_satisfied(solution, edeps, versions,
          disregard_setuptools=True)
    except depresolve.MissingDependencyInfoError as e:
      errstring = 'Unable to determine if satisfied: missing dep info for ' + \
          str(e.args[1])
      satisfied = ''   # evaluates False but is not False
      logger.error(errstring + '. Resolution for ' + distkey + ' unknown. ' +
          ' Full exception:' + str(e))


  # Use venv catalog to print debug info. Clunky.
  global venv_catalog
  if venv_catalog is None:
    venv_catalog = depdata.load_json_db(VENV_CATALOG_JSON_FNAME)

  logger.info('Tried solving ' + distkey + ' using rbtcollins pip patch. '
      'Installed: ' + str(installed) + '. Satisfied: ' + str(satisfied) +
      ' virtualenv used: ' + venv_catalog[distkey])

  # Return the solution that rbt generates for this distkey:
  #  - whether or not the distkey itself was installed
  #  - whether or not the install set is fully satisfied and conflict-less
  #  - what the solution set is
  #  - error string if there was an error
  return (installed, satisfied, solution, errstring, stderr_installation)





def rbt_backtracking_satisfy(distkey, edeps, versions_by_package, local=False,
    dir_rbt_pip='../pipcollins'):
  """
  Determine correct install candidates by using rbtcollins' pip branch
  issue-988.

  Steps:
    1. Sets up a random-name new virtual environment
    2. Installs rbtcollins' pip patch on that virtual environment
    3. Installs the given distribution using rbt pip
    4. Runs `pip list` and harvests the solution set

  Args & output modeled after resolver.resolvability.backtracking_satisfy().

  Additional, optional argument:
   - local (optional):
        - if not provided, we connect to PyPI
        - if simply set to 'True', we use the default local bandersnatch
          location for the simple listing of packages,
          'file:///srv/pypi/web/simple'.
        - if another value is provided, we interpret it as a string indicating
          the location of the simple index listing of packages on the mirror
          to use.

  Returns:
    - solution: the list of distributions to install to satisfy all of the
      given distkey's dependencies (and all their dependencies and so on). In
      other words, an install candidate set that should include the given
      distkey and provide for a functioning environment.
    - std_err: a string (stderr.read().decode()) that contains the stderr from
      the process running the pip install command for the distribution, using
      rbtcollins' pip branch. This is potentially helpful in the case of
      errors.

  Raises:
    - UnrelatedInstallFailure if creation of a virtualenv fails (before we even
      get to the point of trying to install the dist). Should probably just be
      retried right away.

  """

  logger = depresolve.logging.getLogger(
      'rbtpip_integrate.rbt_backtracking_satisfy')

  assert distkey == distkey.lower(), 'distkeys should always be lowercase!' + \
      distkey + ' is not!'  # Remember not to use distkey.islower(). Bug.

  ###############
  # Steps 1 and 2: Create venv and install rbt pip.
  venv_name = 'v3_'
  for i in range(0,7):
    venv_name += random.choice(string.ascii_lowercase + string.digits)

  # Save a map of this virtual environment name to distkey for later auditing
  # if interesting things happen.
  global venv_catalog
  if venv_catalog is None:
    venv_catalog = depdata.load_json_db(VENV_CATALOG_JSON_FNAME)
  venv_catalog[distkey] = venv_name
  json.dump(venv_catalog, open(VENV_CATALOG_JSON_FNAME, 'w'))


  cmd_venvcreate = 'virtualenv -p python3 --no-site-packages ' + VENVS_DIR + \
      '/' + venv_name
  cmd_sourcevenv = 'source ' + VENVS_DIR + '/' + venv_name + '/bin/activate'
  cmd_piplist = cmd_sourcevenv + '; pip list -l --disable-pip-version-check'
  cmd_install_rbt_pip = cmd_sourcevenv + '; cd ' + dir_rbt_pip + \
      '; pip install -e . --disable-pip-version-check'
  #cmd_check_pip_ver = cmd_sourcevenv + '; pip --version'
  #cmd_install_seb_pip = cmd_sourcevenv + '; cd ' + dir_seb_pip + '; pip install -e .'
  #cmd_install_depresolve = cmd_sourcevenv + '; cd ' + dir_depresolve + '; pip install -e .'


  # Create venv
  logger.info('For ' + distkey + ', creating virtual environment ' + venv_name)
  stdout, stderr = popen_wrapper(cmd_venvcreate)

  # Validate the venv by trying to source it. Sometimes this goes wrong....
  # I don't know why yet.
  stdout, stderr = popen_wrapper(cmd_sourcevenv)
  if 'No such file or directory' in stderr:
    raise UnrelatedInstallFailure('Failed to create the virtual environment ' +
        venv_name + ' for dist ' + distkey + ' installation. bin/activate is '
        'missing.')
  else:
    logger.info('For ' + distkey + ', venv '  + venv_name + 'looks OK.')


  ## Initial snapshot of installed packages
  #popen_wrapper(cmd_piplist)


  # Install rbtcollins' issue_988 pip branch and display pip version
  # (should then be 8.0.0dev0)
  logger.info('For ' + distkey + ', installing rbt_pip in ' + venv_name)
  popen_wrapper(cmd_install_rbt_pip)
  #popen_wrapper(cmd_check_pip_ver)



  ###############
  # Step 3: Install given dist using rbt pip.

  # Deconstruct distkey into package and version for pip.
  packname = depdata.get_packname(distkey)
  version_string = depdata.get_version(distkey)
  # Construct as a requirement for pip install command.
  requirement = packname + '==' + version_string


  # Put together the pip command.

  # First, are we using PyPI or a specified (local) mirror?
  index_optional_args = ''
  if local == True: # If local is just the value True, use default local mirror
    index_optional_args = '-i file:///srv/pypi/web/simple'

  elif local: # If local is a specific string, assume it's the index location.
    index_optional_args = '-i ' + local

  else:
    pass # Proceed normally, using PyPI, not adding index arguments.

  # Would love to be able to just call
  # scraper._call_pip_with_timeout(pip_arglist), but can't because we have to
  # do this in a virtual environment, so doing it this way instead:
  cmd_install_dist = cmd_sourcevenv + \
      '; pip install --disable-pip-version-check --quiet ' + \
      index_optional_args + ' ' + requirement

  logger.info('For ' + distkey + ', using rbtpip to install in ' + venv_name)

  # Install using rbtcollins pip, incorporating a 5 min timeout, and taking
  # the std_err output (which comes out as a bytes object which we
  # auto-decode).
  stdout_installation, stderr_installation = popen_wrapper(cmd_install_dist)

  # Print output, if there is any.
  if stdout_installation:
    logger.info('Installation process for ' + distkey + ' using rbtpip yields '
        'stdout: ' + stdout_installation)

  if stderr_installation:
    logger.warn('Installation process for ' + distkey + ' using rbtpip yields '
        'stderr: ' + stderr_installation)



  ###############
  # Step 4: Run `pip list` and harvest the solution set
  # Initial snapshot of installed packages
  stdout_list, stderr_list = popen_wrapper(cmd_piplist)
  piplist_output = stdout_list.splitlines()

  solution = []

  # Convert list_output into solution set here.

  for line in piplist_output:

    # pip list outputs almost-distkeys, like: 'pbr (0.11.1)'.
    # We cut out the space, lowercase, and pray they work. /:
    installed_distkey = line.replace(' ', '').lower()

    # These distributions are installed when a new virtual environment is
    # created, so ignore them. This is an unpleasant hack: some packages
    # actually declare dependencies on these, and so the stored solutions may
    # be incomplete, and there's a hack in is_dep_satisfied to disregard these
    # when given disregard_setuptools=True.
    # Also note that because pip here is installed using -e option, it'll show
    # up as having more than just the version string in the ()s where its
    # version string is expected: 'pip (8.0.0.dev0, /Users/s/w/pipcollins)'
    # Since we're excluding pip here anyway, we don't have to deal with that.
    if installed_distkey.startswith('wheel(') or \
        installed_distkey.startswith('pip(') or \
        installed_distkey.startswith('setuptools('):
      continue

    solution.append(installed_distkey)

  return solution, stderr_installation





@timeout.timeout(300) # Timeout after 5 minutes.
def popen_wrapper(cmd, return_stderr=False):
  """
  Just runs subprocess.popen with the given command, waits, and returns the
  output (stdout and stderr, decoded from bytes into strings).
  Times out after 5 minutes.
  """
  sub_obj = subprocess.Popen(cmd, shell=True, executable='/bin/bash',
      stdout=subprocess.PIPE, stderr=subprocess.PIPE)

  (stdout, stderr) = sub_obj.communicate()

  return stdout.decode(), stderr.decode()






def main():
  """
  Choose some conflicting dists to test rbtcollins solver on.

    Steps:
    1. Load dependency data.

    2. Call rbttest to solve using rbtcollins' pip branch issue-988 and
       determine the correctness of that solution.

    3. Write all the solution sets and correctness info to a json file.

  """

  logger = depresolve.logging.getLogger('rbtpip_integrate.main')

  # Create virtual environments directory if it doesn't exist.
  if not os.path.exists(VENVS_DIR):
    os.makedirs(VENVS_DIR)


  distkeys_to_solve = []

  n_distkeys = 3 # default 3, overriden by argument --n=, or specific distkeys

  args = sys.argv[1:]
  noskip = False
  local = False
  all_conflicting = False

  if args:
    for arg in args:
      if arg == '--noskip':
        noskip = True
      elif arg == '--local':
        local = True
      elif arg.startswith('--local='):
        local = arg[8:]
      elif arg.startswith('--n='):
        n_distkeys = int(arg[4:])
      elif arg == '--all':
        local = True
        all_conflicting = True
      else:
        try:
          distkeys_to_solve.append(depdata.normalize_distkey(arg))
        except Exception as e:
          print('Unable to normalize provided argument as distkey: ' +
              str(arg) + '. Please provide correct arguments.')
          raise


  # If we didn't get any specific distkeys to solve for from the args, then
  # pick randomly:

  if distkeys_to_solve:
    n_distkeys = len(distkeys_to_solve)

  else: # not distkeys_to_solve:
    # Randomize from the model 3 conflict list.
    
    depdata.ensure_data_loaded()

    con3 = depdata.conflicts_3_db

    conflicting = [depdata.normalize_distkey(d) for d in con3 if con3[d]]

    if all_conflicting:
      distkeys_to_solve = conflicting

    else:
      import random
      for i in range(0, n_distkeys):
        distkeys_to_solve.append(random.choice(conflicting))



  ###############
  # Step 1: Load dependency data.

  # Load dependencies from their json file, harvested in prior full run of
  # scraper.
  depdata.ensure_data_loaded(include_edeps=True)
  deps = depdata.dependencies_by_dist
  edeps = depdata.elaborated_dependencies # potentially stale!
  versions = depdata.versions_by_package # potentially stale!


  # Prepare solution dictionary.
  solution_dict = depdata.load_json_db(SOLUTIONS_JSON_FNAME)



  ###############
  # Step 2: Run rbttest to solve and test solution.
  try:
    for distkey in distkeys_to_solve:

      if not noskip and distkey in solution_dict:
        logger.info('Skipping rbt solve for ' + distkey + ' (already have '
            'results).')
        continue

      # Try-scoping paranoia.
      installed = None
      satisfied = None
      solution = None
      errstring = None
      stderr_installation = None

      try:
        # Explicit with multiple variables for clarity for the reader.
        (installed, satisfied, solution, errstring, stderr_installation) = \
            rbttest(distkey, edeps, versions, local)
        solution_dict[distkey] = (installed, satisfied, solution, errstring,
            stderr_installation)

      except UnrelatedInstallFailure as e:
        # Installation failed in some trivial way and should be retried once.
        # For example, virtual environment creation failed.
        (installed, satisfied, solution, errstring, stderr_installation) = \
            rbttest(distkey, edeps, versions, local)
        solution_dict[distkey] = (installed, satisfied, solution, errstring,
            stderr_installation)


      # ###############
      # # Step 3: Dump solutions and solution correctness info to file.
      # # Until this is stable, write after every solution so as not to lose data.
      # logger.info('Writing results for ' + distkey)
      # json.dump(solution_dict, open(SOLUTIONS_JSON_FNAME, 'w'))
  
  except:
    print('Encountered ERROR. Saving solutions to file and halting. Error:')
    traceback.print_exc()

  ###############
  # Step 3: Dump solutions and solution correctness info to file.

  finally:
    print('Writing solutions gathered to ' + SOLUTIONS_JSON_FNAME)
    try:
      json.dump(solution_dict, open(SOLUTIONS_JSON_FNAME, 'w'))
    except:
      import ipdb
      ipdb.set_trace()
      print('Tried to write gathered solutions to file, but failed to write.'
          'Entering debug mode to allow data recovery.')




if __name__ == '__main__':
  main()
