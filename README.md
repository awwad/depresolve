# pypi-depresolve
PyPI package dependency resolution project

The purpose of this project is to investigate the problem of package dependency conflict resolution for the Python Package Index (PyPI) and for pip.

analyze_deps_via_pip.py employs a modified pip fork I'm tagging 8.0.0.dev0seb, available at https://github.com/awwad/pip on branch "develop".

By default, it pulls packages straight from PyPI, but can be run using a local .tar.gz sdist, or even from a local bandersnatch'd PyPI mirror. See instructions below.

(TODO: Link first to overview of package conflicts in general. Link to overview of resolvable/unresolvable package conflicts distinction.)

Via modified pip code, this project runs the initial (pre-install) portion of the pip install process for a list of packages. As it does so, it also:
  - Harvests dependency info:
    - Harvests all dependency information that pip extracts from the packages (and packages the packages depend on, and packages *those* packages depend on, etc) and stores it in a dependencies_db.json file stored in the directory from which analyze_deps_via_pip.py is called. (This process is cumulative for additional runs and tries not to duplicate work.)
  - Detects conflits:
    - Detects dependency conflicts via three planned models/definitions of a dependency conflict, and stores (and reads from) information on these in a set of conflicts_<...>_db.json files stored in the directory from which analyze_deps_via_pip.py is called. Avoids work duplication by not repeating for a given package (name and version) if conflict info for that package already exists.
      - In each conflict model, we say that a conflict exists for package R if in the tree, rooted at R, of install candidates selected by pip given an instruction to install package R, some package C is depended on by packages A and B, and...:
        - Model 1: ... and the dependency specification (requirement strings) of packages A and B for package C are not identical (e.g. A depends on C==3.0 and B depends on C>=1, regardless of the available versions). *This encompasses all dependency conflicts, both resolvable and unresolvable.*
        - Model 2: ... and the dependency specification (requirement strings) of packages A and B are such that pip's first choice package (based on its internal prioritization -- TODO: add link to that code here) to resolve those two dependencies would not be the same package. (e.g. A depends on C==3.0 and B depends on C>=1, and the most recent version is > 3.0.) *This encompasses all unresolvable and some resolvable dependency conflicts.*
        - Model 3: ... and pip selects a final set of install candidates that would not fulfil all of those candiates (and the initial) requirement specifications. (e.g. A depends on C==3.0 and B depends on C<=2.5) *This encompasses all unresolvable and some resolvable dependency conflicts. It is, in summary, specifically where pip fails to provide for the user's request.* MODEL 3 IS DONE BUT IN TESTING
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
13. python analyze_deps_via_pip.py "motorengine(0.7.4)" --noskip      # (to run this on version 0.7.4 of package motorengine, from remote PyPI, not skipping if the package has already been analyzed, using conflict model 3. This example has a model 3 conflict, so you should see an error explaining that.)

Detailed info on calling the script:

```
Argument handling:
 DEPENDENCY CONFLICT MODELS (see README)
  --cm1    run using conflict model 1 (all resolvable and unresolvable conflicts; see README)
  --cm2    run using conflict model 2 (all unresolvable and some resolvable conflicts; see README)
  --cm3    run using conflict model 3 (default; basically "would pip get this right?"; see README)

 GENERAL ARGUMENTS:
  --noskip Don't skip packages in the blacklist or packages for which information on
           whether or not a conflict occurs is already stored.

 REMOTE OPERATION:   (DEFAULT!)
   ANY ARGS NOT MATCHING the other patterns are interpreted as what I will refer to as 'distkeys':
     packagename(packageversion)
     e.g.:   "django(1.8)"
     Using one of these means we're downloading from PyPI, per pip's defaults.
     Your shell will presumably want these arguments passed in quotes because of the parentheses.


 LOCAL OPERATION: For use when operating with local sdist files (e.g. with a bandersnatched local PyPI mirror)
  --local=FNAME  specifies a local .tar.gz sdist to inspect for dependency conflicts with pip
                 for dependency conflicts
                 e.g. '--local=/srv/pypi/web/packages/source/M/motorengine/motorengine-0.7.4.tar.gz'
                 You can specify as many of these as you like with separate --local=<file> arguments.
                 Local and remote execution are mutually exclusive.
  --local  Using this without "=<file.tar.gz>" means we should alphabetically scan from the local PyPI mirror.
           This is mutually exclusive with the --local=<fname> usage above. If files are specified, we only
           check the files specified.

  --n=N    For use only with --local (not remotes, not --local=<file>).
           Sets N as the max packages to inspect when pulling alphabetically from local PyPI mirror.
           e.g. --n=1  or  --n=10000
           Default for --local runs, if this arg is not specified, is all packages in the entire local PyPI
           mirror at /srv/pypi)
           (TODO: Must confirm that using this arg won't impact remote operation, just for cleanliness.)



  EXAMPLE CALLS:

     ~~ Run on a single package (in this case, arnold version 0.3.0) pulled from remote PyPI,
        using conflict model 3 (default):

         >  python analyze_deps_via_pip.py "arnold(0.3.0)"


     ~~ Run on a few packages from PyPI, using conflict model 2, and without skipping even if
        conflict info on those packages is already available, or if they're in the blacklist for
        having hit unexpected errors in previous runs:

         >  python analyze_deps_via_pip.py "motorengine(0.7.4)" "django(1.6.3)" --cm2 --noskip


     ~~ Run on a single specified package, motorengine 0.7.4, stored locally, using conflict model 2:

         >  python analyze_deps_via_pip.py --cm2 --local=/srv/pypi/web/packages/source/M/motorengine/motorengine-0.7.4.tar.gz

     ~~ Run on the first 10 packages in the local pypi mirror (assumed /srv/pypi) alphabetically,
         using conflict model 1.

         >  python analyze_deps_via_pip.py --cm1 --local --n=10
```  


Comments on manual_package_dependency_extraction.py: 
This script handles manual parsing of setup.py files, without employing pip, and simply extracts dependencies. It is no longer in use and is replaced by analyze_deps_via_pip.py.
