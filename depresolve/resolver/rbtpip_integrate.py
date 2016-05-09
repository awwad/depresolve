"""
<Program Name>
  test_rbtpip.py

<Purpose>
  A script to test rbtcollins' backtracking resolver patch for pip, using
  some depresolve code to do analysis.
"""

import subprocess # shell commands to create and use virtual environments
import random, string # randomized naming for virtual environments
import json
import depresolve
import depresolve.deptools as deptools
import depresolve.depdata as depdata
import depresolve.resolver.resolvability as ry
import depresolve._external.timeout as timeout
#import depresolve.scrape_deps_and_detect_conflicts as scraper

def rbttest(distkeys):
  """
  Steps:
    1. Load dependency data.

    2. Solve using rbtcollins' pip branch issue-988:
       For each distkey, create a new virtual environment, install rbtcollins'
       pip version within it, use it to install the dist indicated, and use
       pip freeze to determine what it installed.    

    3. Run resolvability.are_fully_satisfied to test the solution set for
       consistency.

    4. Write all the solution sets to a json file.

  """




  ###############
  # Step 1 Alternative: Load dependency data.

  # Load dependencies from their json file, harvested in prior full run of
  # scraper.
  depdata.ensure_data_loaded()
  deps = depdata.dependencies_by_dist

  # Make catalog of versions by package from deps info.
  versions = deptools.generate_dict_versions_by_package(deps)

  # Elaborate the dependencies using information about available versions.
  #edeps = deptools.elaborate_dependencies(deps, versions)
  # EDIT: this is very time consuming and we may be dealing with the full
  # dependency data, so instead I'm going to load already-elaborated
  # dependencies. NOTE THAT THIS IS NOT AUTOMATICALLY REFRESHED AND SO IF THERE
  # IS MORE DEPENDENCY DATA ADDED, ELABORATION SHOULD BE DONE OVER. (The full
  # data set may take 30 minutes to elaborate!)
  edeps = depdata.load_json_db('data/elaborated_dependencies.json') # potentially STALE!


  # Prepare solution dictionary.
  solution_dict = depdata.load_json_db('data/solutions_via_rbtpip.json')

  solution_conflicts = depdata.load_json_db(
      'data/solutions_via_rbtpip_conflicts.json')


  ###############
  # Step 2
  # For every distkey we're given, figure out the install candidate solution.
  for distkey in distkeys:

    # Run rbtcollins' pip branch to find the solution, with some acrobatics.
    solution = rbt_backtracking_satisfy(distkey, edeps, versions)

    # Save the solution rbt generates for this distkey.
    solution_dict[distkey] = solution


    ###############
    # Step 3: Run resolvability.are_fully_satisfied to test the solution set
    # for consistency.

    # Test the solution.
    success = False
    if distkey not in solution:
      # If the given solution doesn't even include the distribution to install
      # itself, it's obviously not been successful.
      print('rbt pip failed to install the indicated distkey.')
      assert not solution, 'Programming error. If ' + distkey + ' itself ' + \
          'is not in solution, and something else is, that makes no ' + \
          'sense. Solution was: ' + str(solution)

    else:
      # If it's in there, then we check to see if the solution is fully
      # satisfied.
      success = ry.are_fully_satisfied(solution, edeps, versions)

    venv_catalog = depdata.load_json_db('data/rbtpip_venv_catalog.json')

    print('Successful in solving ' + distkey + ' using rbtcollins pip patch? '
        + str(success) + '. virtualenv used: ' + venv_catalog[distkey])

    # Save success as whether or not a conflict was detected.
    solution_conflicts[distkey] = not success


    ###############
    # Step 4: Dump solutions to file.

    # Until this is stable, write after every solution so as not to lose data.
    json.dump(solution_dict, open('data/solutions_via_rbtpip.json','w'))
    json.dump(solution_conflicts, open(
        'data/solutions_via_rbtpip_conflicts.json','w'))




  ###############
  # Step 4: Dump solutions to file.
  
  # Currently writing after every solution instead.

  # # Write all gathered solutions to json at end.
  # # Save gathered solutions to json.
  # json.dump(solution_dict, open('data/solutions_via_rbtpip.json','w'))






def rbt_backtracking_satisfy(distkey, edeps, versions_by_package):
  """
  Determine correct install candidates by using rbtcollins' pip branch
  issue-988.

  Steps:
    1. Sets up a random-name new virtual environment
    2. Installs rbtcollins' pip patch on that virtual environment
    3. Installs the given distribution using rbt pip
    4. Runs pip freeze and harvests the solution set

  Args & output modeled after resolver.resolvability.backtracking_satisfy().

  """

  # Constants
  dir_rbt_pip = '/Users/s/w/pipcollins'

  ###############
  # Steps 1 and 2: Create venv and install rbt pip.
  venv_name = 'v3_'
  for i in range(0,5):
    venv_name += random.choice(string.ascii_lowercase + string.digits)

  # Save a map of this virtual environment name to distkey for later auditing
  # if interesting things happen.
  venv_catalog = depdata.load_json_db('data/rbtpip_venv_catalog.json')
  venv_catalog[distkey] = venv_name
  json.dump(venv_catalog, open('data/rbtpip_venv_catalog.json','w'))


  cmd_venvcreate = 'virtualenv -p python3 --no-site-packages ' + venv_name
  cmd_sourcevenv = 'source ' + venv_name + '/bin/activate'
  cmd_pipfreeze = cmd_sourcevenv + '; pip freeze'
  cmd_install_rbt_pip = cmd_sourcevenv + '; cd ' + dir_rbt_pip + '; pip install -e .'
  cmd_check_pip_ver = cmd_sourcevenv + '; pip --version'
  #cmd_install_seb_pip = cmd_sourcevenv + '; cd ' + dir_seb_pip + '; pip install -e .'
  #cmd_install_depresolve = cmd_sourcevenv + '; cd ' + dir_depresolve + '; pip install -e .'

  # Create venv
  popen_wrapper(cmd_venvcreate)

  # Initial snapshot of installed packages
  popen_wrapper(cmd_pipfreeze)

  # Install rbtcollins' issue_988 pip branch and display pip version
  # (should then be 8.0.0dev0)
  popen_wrapper(cmd_install_rbt_pip)
  popen_wrapper(cmd_check_pip_ver)



  ###############
  # Step 3: Install given dist using rbt pip.

  # Deconstruct distkey into package and version for pip.
  packname = depdata.get_packname(distkey)
  version_string = depdata.get_version(distkey)
  # Construct as a requirement for pip install command.
  requirement = packname + '==' + version_string


  # Put together the pip command.

  # Nope: can't do it this way because I need to use the virtual environment.
  ## pip_arglist = [
  ##   'install',
  ##   requirement,
  ##   '--disable-pip-version-check',
  ##   '--quiet']
  ### Call pip with a 5 minute timeout.
  ##exitcode = scraper._call_pip_with_timeout(pip_arglist)

  # Have to do it this way instead:
  cmd_install_dist = cmd_sourcevenv + \
      '; pip install --disable-pip-version-check --quiet ' + requirement

  popen_wrapper(cmd_install_dist) # have incorporated 5 min timeout




  ###############
  # Step 4: Run pip freeze and harvest the solution set
  # Initial snapshot of installed packages
  freeze_output = subprocess.Popen(cmd_pipfreeze, shell=True,
      stdout=subprocess.PIPE).stdout.readlines()

  # Now I have to parse out the actual installs from the output... /:
  # It looks like this, for example, in python3:
  #[b'cffi==1.5.0\n',
  # b'cryptography==1.2.2\n',
  # b'idna==2.0\n',
  # b'iso8601==0.1.11\n',
  # b'pyasn1==0.1.9\n',
  # b'pycparser==2.14\n',
  # b'pycrypto==2.6.1\n',
  # b'PyNaCl==1.0.1\n',
  # b'six==1.10.0\n',
  # b'tuf==0.10.0\n',
  # b'wheel==0.26.0\n']

  solution = []

  # Convert freeze_output into solution set here.

  # Yeah, this isn't really kosher, and it probably breaks in python2.
  # Principle for this week: first, get it to work.
  for line in freeze_output:

    installed_package = line.decode()[:-1] # decode and cut off \n at end (assumption: actual newline)

    # Split it into package name and version:
    (name, ver) = installed_package.split('==')

    # Put it together into a distkey.
    installed_distkey = depdata.distkey_format(name, ver)

    # These virtual environments start with wheel 0.26.0, so ignore it.
    if installed_distkey == 'wheel(0.26.0)':
      continue

    solution.append(installed_distkey)

  return solution





@timeout.timeout(300) # Timeout after 5 minutes.
def popen_wrapper(cmd):
  """
  Just runs subprocess.popen with the given command and prints the output to
  the screen. Times out after 5 minutes.
  """
  print(subprocess.Popen(cmd, shell=True,
      stdout=subprocess.PIPE).stdout.readlines())





def main():
  """
  Randomly choose some conflicting dists to test rbtcollins solver on.
  """
  con3 = depdata.load_json_db('data/conflicts_3.json')
  conflicting = [p for p in con3 if con3[p]]
  import random
  distkeys_to_solve = []
  for i in range(0,10):
    distkeys_to_solve.append(random.choice(conflicting))

  rbttest(distkeys_to_solve)




if __name__ == '__main__':
  main()
