"""
<Program Name>
  installer.py

<Purpose>
  The primary function here is install_and_report, which, given a set of
  candidates, installs them in a fresh virtual environment and reports back on
  the status of the installation:
    - whether the full set of distributions indicated was installed


"""

import subprocess # shell commands to create and use virtual environments
import random, string # randomized naming for virtual environments
import sys # for arguments to main
import os # for directory creation
import depresolve
logger = depresolve.logging.getLogger('depresolve')
import depresolve.depdata as depdata
import depresolve.resolver.resolvability as ry
import depresolve._external.timeout as timeout

VENVS_DIR = 'installer_venvs'





def install_and_report(solution, local=False, dir_pip=None):
  """

  Accepts a list of distkeys indicating what distributions to try to install
  using pip.

  Arguments:
    - solution: a list of distkeys indicating what distributions to install
    - local (optional):
        - if not provided, we connect to PyPI
        - if simply set to 'True', we use the default local bandersnatch
          location for the simple listing of packages,
          'file:///srv/pypi/web/simple'.
        - if another value is provided, we interpret it as a string indicating
          the location of the simple index listing of packages on the mirror
          to use.
    - dir_pip (optional): If a special version of pip is to be used, this
      is the directory where it resides. If left as None, we simply use the
      default version of pip installed with virtualenv. If provided, we'll use
      'pip install -e .' to install it.


  Returns:
    - venv: The directory containing the virtual environment created for this
      install.
    - stderr_installation: stderr.read().decode() for the pip install
      subprocess command that installed the distribution. In case of install
      errors. Empty string if stderr was empty.

  Raises:
    - UnrelatedInstallFailure if the the installation fails in some trivial way
      that merits trying again.


  Steps:
    1. Sets up a random-name new virtual environment
    2. Installs the given distributions using pip
  """
  errstring = ''

  # Argument processing: Sanitize solution set distkeys.
  try:
    solution = [depdata.normalize_distkey(distkey) for distkey in solution]
  except Exception, e:
    logger.error('Unable to sanitize distkeys in the solution provided. '
        'Solution: ' + str(solution))
    raise


  ###############
  # Step 1:
  # Create the virtual environment (venv) and validate it by trying to source
  # it. Sometimes this goes wrong. I don't know why yet.
  venv_dir = None

  # Try to create a venv up to three times.
  success = False
  while not success:
    logger.info('Trying to create new virtual environment.')
    try:
      venv_dir = create_venv()
    except UnrelatedInstallFailure:
      logger.error('Failed to create virtual environment.')
    else:
      success = True
      logger.info('Successfully created virtual environment: ' + venv_dir)


  # To use it, we'll have to source it before any other command.
  cmd_sourcevenv = get_source_venv_cmd_str(venv_dir)


  # If we've been given a specific pip to install, we use that instead of
  # leaving the default.
  if dir_pip is not None:
    logger.info('Instructed to use custom pip @ ' + dir_pip + '. Installing '
        'that custom pip version into venv ' + venv_dir)
    cmd_install_custom_pip = cmd_sourcevenv + '; cd ' + dir_pip + \
        '; pip install -e . --disable-pip-version-check'
    stdout, stderr = popen_wrapper(cmd_install_custom_pip)

    # Consider checking for failure here.

    #cmd_check_pip_ver = cmd_sourcevenv + '; pip --version'



  

  logger.info('Starting installation in venv ' + venv_dir + ' of solution '
      'set: ' + str(solution))

  install_into_venv(solution, venv_dir, local)






  

  # Return the solution that rbt generates for this distkey:
  #  - whether or not the distkey itself was installed
  #  - whether or not the install set is fully satisfied and conflict-less
  #  - what the solution set is
  #  - error string if there was an error
  return (venv_name, stderr_installation)





def install_into_venv(distkeys, venv_dir, local=False):
  """
  Given a list of distkeys, install those distributions into the given virtual
  environment.

  Args:
    - distkeys: list of distribution keys (see depdata.py, e.g. 'Django(1.8)')
    - venv_dir: the directory of a virtual environment, e.g. 'venvs/v3_zzzzzz',
      if venvs/v3_zzzzzz/bin/activate is the virtual environment's activate
      script.
    - local: Default False. If False, get packages from PyPI; if True, get
      packages from index on local filesystem: /srv/pypi/web/simple (local
      mirror); if a non-empty string, use the given string as the index
      location - e.g. 'file:///srv/pypi/web/simple'.
  """

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

  # Install using pip, incorporating a 5 min timeout, and taking the std_err
  # output (which comes out as a bytes object which we auto-decode).
  stdout_installation, stderr_installation = popen_wrapper(cmd_install_dist)

  # Print output, if there is any.
  if stdout_installation:
    logger.info('Installation process for ' + distkey + ' using pip yields '
        'stdout: ' + stdout_installation)

  if stderr_installation:
    logger.warn('Installation process for ' + distkey + ' using pip yields '
        'stderr: ' + stderr_installation)







def create_venv():
  """
  Creates a randomly named virtual environment and returns its directory name.

  Raises (does not catch) UnrelatedInstallFailure if unable to create valid
  virtual environment on first attempt.
  """
  venv_dir = VENVS_DIR + '/v3_'
  for i in range(0,7):
    venv_name += random.choice(string.ascii_lowercase + string.digits)

  cmd_venvcreate = 'virtualenv -p python3 --no-site-packages ' + venv_dir

  logger.info('For ' + distkey + ', creating virtual environment ' + venv_dir)
  stdout, stderr = popen_wrapper(cmd_venvcreate)

  validate_venv(venv_dir)

  return venv_dir





def get_source_venv_cmd_str(venv_dir):
  return 'source ' + venv_dir + '/bin/activate'





def validate_venv(venv_dir):
  """
  Given the name of a directory containing a virtual environment
  """
  cmd_sourcevenv = get_source_venv_cmd_str(venv_dir)

  stdout, stderr = popen_wrapper(cmd_sourcevenv)
  if 'No such file or directory' in stderr:
    raise UnrelatedInstallFailure('Failed to create the virtual environment ' +
        venv_name + ' for dist ' + distkey + ' installation. bin/activate is '
        'missing.')
  else:
    logger.info('For ' + distkey + ', venv '  + venv_name + ' looks OK.')





@timeout.timeout(300) # Timeout after 5 minutes.
def popen_wrapper(cmd):
  """
  Just runs subprocess.popen with the given command, waits, and returns the
  output (stdout and stderr, decoded from bytes into strings).
  Times out after 5 minutes.
  """
  sub_obj = subprocess.Popen(cmd, shell=True, executable='/bin/bash',
      stdout=subprocess.PIPE, stderr=subprocess.PIPE)

  (stdout, stderr) = sub_obj.communicate()

  return stdout.decode(), stderr.decode()
