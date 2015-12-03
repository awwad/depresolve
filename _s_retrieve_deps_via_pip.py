# <~> Retrieve dependencies via pip.

import pip
import os

#pip.main(['install', '-d', '/Users/s/w/git/pypi-depresolve/temp_distros', '-i', 'file:///srv/pypi/web/simple', 'python-twitter'])


BANDERSNATCH_MIRROR_DIR = '/srv/pypi/web/packages/source/'
SDIST_FILE_EXTENSION = '.tar.gz' # assume the archived packages bandersnatch grabs end in this
DEBUG__N_SDISTS_TO_PROCESS = 55 # debug; max packages to explore during debug

def main():
  list_of_sdists_to_inspect = []

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

    # If we're supposed to be using pip instead of doing all the parsing ourselves,
    #   then (assuming it's my pip fork version 8.0.0.dev0seb), run pip with the
    #   appropriate arguments.
    formatted_requirement = packagename + "==" + deduced_version_string
    exitcode = pip.main(['install', '-d', '/Users/s/w/git/pypi-depresolve/temp_distros', '--find-dep-conflicts', '-i', 'file:///srv/pypi/web/simple', formatted_requirement])
    if exitcode == 2:
      print("<~> X  SDist",packagename_withversion,": pip found A DEPENDENCY CONFLICT.")
    else:
      print("<~> .  SDist",packagename_withversion,": pip found no dependency conflicts.")
    continue





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
#     I'll go with that assumption.
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
