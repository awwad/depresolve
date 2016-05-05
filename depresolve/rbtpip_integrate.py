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

def rbttest(distkey):
  """
  Steps:
  1. Runs scraper for a distkey (from a specific pre-configured virtual environment, using seb pip)
  2. Sets up a random-name new virtual environment
  3. Installs rbtcollins' pip patch on that virtual environment
  4. Installs the given distribution using rbt pip
  5. Runs pip freeze and harvests the solution set
  6. Runs resolvability.are_fully_satisfied to test the solution set for consistency.
  """

  # Constants
  dir_rbt_pip = '/Users/s/w/pipcollins'
  dir_seb_pip = '/Users/s/w/pipdevelop'
  dir_depresolve = '/Users/s/w/depresolve'
  dir_seb_venv = '/Users/s/w/depresolve/v3p'


  ###############
  # Step 1: Collect the dependencies for the given distkey by running my
  # scraper n a virtualenv already set up for depresolve.
  # Yes, this is going from python into a shell into another python instance.
  # I'm not going to figure out how to essentially employ a separate virtualenv
  # from within a python instance right now.
  cmd_source_seb_venv = 'source ' + dir_seb_venv + '/bin/activate'
  cmd_scrape = cmd_source_seb_venv + \
      '; cd ' + dir_depresolve + \
      '; python depresolve/scrape_deps_and_detect_conflicts.py ' + \
      ''

  ###############
  # Steps 2 and 3: Create venv and install rbt pip.
  venv_name = 'v3_'
  for i in range(0,5):
    venv_name += random.choice(string.ascii_lowercase + string.digits)

  cmd_venvcreate = 'virtualenv -p python3 --no-site-packages ' + venv_name
  cmd_sourcevenv = 'source' + venv_name + '/bin/activate'
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
  # Step 4: Install given dist using rbt pip.

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
  cmd_install_dist = cmd_sourcevenv + '; pip install ' + requirement + \
      ' --quiet --disable-pip-version-check'

  popen_wrapper(cmd_install_dist) # have incorporated 5 min timeout




  ###############
  # Step 5: Run pip freeze and harvest the solution set
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

    solution.append(installed_distkey)




  ###############
  # Step 6: Run resolvability.are_fully_satisfied to test the solution set for
  # consistency.

  # Load dependencies from the json file that the scraper wrote to in Step 1.
  deps = depdata.dependencies_by_dist
  # Make catalog of versions by package from deps info.
  versions = deptools.generate_dict_versions_by_package(deps)
  # Elaborate the dependencies using information about available versions.
  edeps = deptools.elaborate_dependencies(deps, versions)

  # Test the solution.
  success = ry.are_fully_satisfied(solution, edeps, versions)

  print('Successful in solving ' + distkey + ' using rbtcollins pip patch? '
      + str(success))

  
  # Save solution to json.
  solution_dict = json.load(open('data/solutions_via_rbtpip.json','r'))
  solution_dict[distkey] = solution
  json.dump(solution_dict, open('data/solutions_via_rbtpip.json','w'))






@timeout.timeout(300) # Timeout after 5 minutes.
def popen_wrapper(cmd):
  """
  Just runs subprocess.popen with the given command and prints the output to
  the screen. Times out after 5 minutes.
  """
  print(subprocess.Popen(cmd, shell=True,
      stdout=subprocess.PIPE).stdout.readlines())





def main():
  rbttest('motorengine(0.7.4')


if __name__ == '__main__':
  main()
