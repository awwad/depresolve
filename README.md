# pypi-depresolve
PyPI package dependency resolution project

The purpose of this project is to investigate the problem of package dependency conflict resolution for the Python Package Index (PyPI) and for pip.

analyze_deps_via_pip.py employs a modified pip fork I'm tagging 8.0.0.dev0seb, available at https://github.com/awwad/pip on branch "develop".

Currently, it employs (and expects) a local bandersnatch'd mirror of PyPI.

(TODO: Link first to overview of package conflicts in general. Link to overview of resolvable/unresolvable package conflicts distinction.)

Via modified pip code, this project runs the initial (pre-install) portion of the pip install process for a list of packages. As it does so, it also:
  - Harvests dependency info:
    - Harvests all dependency information that pip extracts from the packages (and packages the packages depend on, and packages *those* packages depend on, etc) and stores it in a dependencies_db.json file stored in the directory from which analyze_deps_via_pip.py is called. (This process is cumulative for additional runs and tries not to duplicate work.)
  - Detects conflits:
    - Detects dependency conflicts via two (of three planned) models/definitions of a dependency conflict, and stores (and reads from) information on these in a set of conflicts_<...>_db.json files stored in the directory from which analyze_deps_via_pip.py is called. Avoids work duplication by not repeating for a given package (name and version) if conflict info for that package already exists.
      - In each conflict model, we say that a conflict exists for package R if in the tree, rooted at R, of install candidates selected by pip given an instruction to install package R, some package C is depended on by packages A and B, and...:
        - Model 1: ... and the dependency specification (requirement strings) of packages A and B for package C are not identical (e.g. A depends on C==3.0 and B depends on C>=1, regardless of the available versions). *This encompasses all dependency conflicts, both resolvable and unresolvable.*
        - Model 2: ... and the dependency specification (requirement strings) of packages A and B are such that pip's first choice package (based on its internal prioritization -- TODO: add link to that code here) to resolve those two dependencies would not be the same package. (e.g. A depends on C==3.0 and B depends on C>=1, and the most recent version is > 3.0.) *This encompasses all unresolvable and some resolvable dependency conflicts.*
        - Model 3: ... and pip selects a final set of install candidates that would not fulfil all of those candiates (and the initial) requirement specifications. (e.g. A depends on C==3.0 and B depends on C<=2.5) *This encompasses all unresolvable and some resolvable dependency conflicts. It is, in summary, specifically where pip fails to provide for the user's request.* MODEL 3 IS UNDER DEVELOPMENT AND NOT YET FINISHED.
  - Blacklists packages:
    - Produces & reads from a blacklist_db.json file (in the directory from which analyze_deps_via_pip.py is called) that prevents packages that pip code is unable to parse from being touched again by this project while running with the same major version of python. This addresses the issue of a substantial fraction of packages being installable only on a python 3 environment (or only on a python 2 environment), along with the issue of badly behaved packages that pip would not be able to install, along with the issue of (old) packages that are not compliant with the current version of pip and that pip would no longer be able to install.

Note that all skipping based on blacklisting or data on the existence / lack of a conflict for a given package (package name & version) can be avoided by use of argument --noskip.

Instructions for use:

1.  git clone https://github.com/awwad/pip.git
2.  cd pip
3.  git checkout develop
4.  cd ..
5.  git clone https://github.com/awwad/pypi-depresolve.git
6.  virtualenv -p python3 --no-site-packages v3
7.  source v3/bin/activate
8.  cd pip
9.  pip install -e .     # (For your convenience, this installs in editable mode. Reference here: https://pip.pypa.io/en/stable/reference/pip_install/#editable-installs )
10. cd ../pypi-depresolve
13. python analyze_deps_via_pip.py --n=1 --cm2 --noskip      # (to run this for 1 package, the first 1 in the mirror alphabetically, employing conflict model 2, and not skipping if the package has already been analyzed)
  


Comments on manual_package_dependency_extraction.py: 
This script handles manual parsing of setup.py files, without employing pip, and simply extracts dependencies. It is no longer in use and is replaced by analyze_deps_via_pip.py.