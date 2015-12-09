# <~> Retrieve dependencies via pip version 8.0.0.dev0.seb

import sys # for arguments and exceptions
import pip
import os
import json

#pip install -d /Users/s/w/git/pypi-depresolve/temp_distros -i file:///srv/pypi/web/simple --find-dep-conflicts $p
#pip.main(['install', '-d', '/Users/s/w/git/pypi-depresolve/temp_distros', '-i', 'file:///srv/pypi/web/simple', '--find-dep-conflicts', python-twitter'])

BANDERSNATCH_MIRROR_DIR = '/srv/pypi/web/packages/source/'
SDIST_FILE_EXTENSION = '.tar.gz' # assume the archived packages bandersnatch grabs end in this
TEMPDIR_FOR_DOWNLOADED_DISTROS = '/Users/s/w/git/pypi-depresolve/temp_distros'
LOCATION_OF_LOCAL_INDEX_SIMPLE_LISTING = 'file:///srv/pypi/web/simple'
_S_DEPENDENCY_CONFLICTS_DB_FILENAME = "/Users/s/w/git/pypi-depresolve/_s_deps_conflicts_from_pip.json"
#WRITE_EVERY_X = 5

def main():
  DEBUG__N_SDISTS_TO_PROCESS = 1 # debug; max packages to explore during debug
  print("_s_retrieve_deps_via_pip - Version 0.1.0")
  list_of_sdists_to_inspect = []

  # Argument processing. If we have arguments coming in, treat those as the sdists to inspect.
  if len(sys.argv) > 1:
    for arg in sys.argv[1:]:
      if arg.startswith("--n="):
        DEBUG__N_SDISTS_TO_PROCESS = int(arg[4:])
      else:
        list_of_sdists_to_inspect.append(arg)

  # If we weren't given sdists to inspect, we'll scan everything in BANDERSNATCH_MIRROR_DIR
  if not list_of_sdists_to_inspect:
    i = 0
    for dir,subdirs,files in os.walk(BANDERSNATCH_MIRROR_DIR):
      for fname in files:
        if is_sdist(fname):
          list_of_sdists_to_inspect.append(os.path.join(dir,fname))
          i += 1
          if i >= DEBUG__N_SDISTS_TO_PROCESS: # awkward control structure, but saving debug run time
            break
      if i >= DEBUG__N_SDISTS_TO_PROCESS: # awkward control structure, but saving debug run time
        break


  # Fetch info on already known conflicts so that we can skip packages below. (Important for python 2 and python 3 runs.)
  conflicts_db_type1 = None
  with open(_S_DEPENDENCY_CONFLICTS_DB_FILENAME,"r") as fobj:
    conflicts_db_type1 = json.load(fobj)
  

  n_inspected = 0
  for tarfilename_full in list_of_sdists_to_inspect:

    # Load some temp variables to use.
    packagename = get_package_name_given_full_filename(tarfilename_full)
    packagename_withversion = get_package_and_version_string_from_full_filename(tarfilename_full)
    deduced_version_string = packagename_withversion[len(packagename)+1:]

    ## Record information about the package for future storage.
    ##    versions_by_package is a dictionary mapping a package name to the list of
    ##      package versions discovered by the dependency finder, e.g.:
    ##          {'potato': ['potato-1.0.0', 'potato-2.0.0'],
    ##           'oracle': ['oracle-5.0'],
    ##           'pasta':  ['pasta-1.0', 'pasta-2.0']}
    ##
    ## If we don't have an entry for this package (e.g. potato) in the versions_by_package
    ##   dict, create a blank one.
    #if packagename not in versions_by_package:
    #  versions_by_package[packagename] = []
    ## Then add this discovered version (e.g. potato-1.1) to the list for its package (e.g. potato)
    #versions_by_package[packagename].append(packagename_withversion)

    # Assuming it's my pip fork version 8.0.0.dev0seb), run pip with the
    #   appropriate arguments.
    formatted_requirement = packagename + "==" + deduced_version_string

    # Some dist filenames have "_" where the package name has "-".
    # To prevent work from being reproduced, we'll account for these.
    packagename_underscores_to_dashes = packagename.replace('_','-')

    # Check to see if we already have conflict info for this package. If so, don't run for it.
    distkey = packagename+"("+deduced_version_string+")" # This is the format for dists in the conflict db.
    distkey_underscores_to_dashes = packagename_underscores_to_dashes+"("+deduced_version_string+")"
    if distkey in conflicts_db_type1 or distkey_underscores_to_dashes in conflicts_db_type1:
      print("<~>    SKIP -- Already have "+distkey+" in db of type 1 conflicts. Skipping. (Now at "+str(n_inspected)+" out of "+str(len(list_of_sdists_to_inspect))+")")
      n_inspected += 1

      #if n_inspected % WRITE_EVERY_X == 0:   #Writing less often to speed this process up.
      #  write_globals_to_db()
      continue
    #else:
    #  import ipdb
    #  ipdb.set_trace()

    exitcode = pip.main(['install', '-d', TEMPDIR_FOR_DOWNLOADED_DISTROS, '--disable-pip-version-check', '--find-dep-conflicts', '-i', LOCATION_OF_LOCAL_INDEX_SIMPLE_LISTING, formatted_requirement])

    if exitcode == 2:
      print("<~> X  SDist",packagename_withversion,": pip errored out (code="+str(exitcode)+"). Possible DEPENDENCY CONFLICT - see db and logs. (Now at "+str(n_inspected)+" out of "+str(len(list_of_sdists_to_inspect))+")")
    elif exitcode == 0:
      print("<~> .  SDist",packagename_withversion,": pip completed successfully. No dependency conflicts observed. (Now at "+str(n_inspected)+" out of "+str(len(list_of_sdists_to_inspect))+")")
    else:
      print("<~> .  SDist",packagename_withversion,": pip errored out (code="+str(exitcode)+"), but it seems to have been unrelated to any dep conflict.... (Now at "+str(n_inspected)+" out of "+str(len(list_of_sdists_to_inspect))+")")
    n_inspected += 1
    #if (n_inspected % WRITE_EVERY_X) == 0:   #Writing less often to speed this process up.
    #  write_globals_to_db()

  # end of for each tarfile/sdist


  #ipdb.set_trace()
  #print("Manually write now!")

  #Writing less often to speed this process up. So writing at end as well. 
  #_s_write_dep_conflicts_global()
  #_s_write_dependencies_global()


# <~> Given a full filename of an sdist (of the form /srv/.../packagename/packagename-1.0.0.tar.gz),
#       return package name and version (e.g. packagename-1.0.0)
def get_package_and_version_string_from_full_filename(fname_full):
  #     get position of last / in full filename
  i_of_last_slash = fname_full.rfind('/')
  #     get position of .tar.gz in full filename
  i_of_targz = fname_full.rfind('.tar.gz')
  return fname_full[i_of_last_slash+1:i_of_targz]



# <~> Given a .tar.gz in a bandersnatch mirror, determine the package name.
#     Bing's code sees fit to assume that the parent directory name is the package name.
#     I'll go with that assumption. (It breaks sometimes with dash/undrescore switching,
#       but we fix that manually.)
def get_package_name_given_full_filename(fname_full):
  return get_parent_dir_name_from_full_path(fname_full)



# <~> Given a fully specified filename (i.e. including its path), extract name of parent directory (without full path).
def get_parent_dir_name_from_full_path(fname_full):
  #     get position of last / in full filename
  i_of_last_slash = fname_full.rfind('/')
  #     get position of 2nd to last / in full filename
  i_of_second_to_last_slash = fname_full[:i_of_last_slash].rfind('/')
  parent_dir = fname_full[i_of_second_to_last_slash+1:i_of_last_slash]

  return parent_dir



# <~> Returns true if the filename given is deemed that of an sdist file, false otherwise.
def is_sdist(fname):
  return fname.endswith(SDIST_FILE_EXTENSION)


if __name__ == "__main__":
  main()


