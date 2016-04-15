"""
<Program Name>
  convert_old_style_deps_to_new_style_deps.py

<Purpose>
  The resolvability branch merge for awwad/depresolve introduces a different
  way of storing dependencies. This script converts from the old to new.

  old:
    deps['foo(0.7.4)']:
         [['pymongo', [['>=', '2.5'], ['!=', '3.0.3']]],
          ['tornado', []]],
          ['motor', []]],
          ['six', []]],
          ['easydict', []]]],

  new:
    deps['foo(0.7.4)']:
         [['pymongo', '>=2.5,!=3.0.3'],
          ['tornado', ''],
          ['motor', ''],
          ['six', ''],
          ['easydict', '']],


  The old format is consistent with a piece of pip's internal specifier
  representations, and the new format is consistent with pip's SpecifierSets,
  which are much more useful. The switch resolves some bugs and makes things
  easier to code and read.

"""

import depresolve.depdata as depdata
from deptools import spectuples_to_specstring


depdata.ensure_data_loaded()

new_deps = dict()


for distkey in depdata.dependencies_by_dist:
  
  my_deps = depdata.dependencies_by_dist[distkey]
  new_deps[distkey] = []

  for dep in my_deps: # for every one of its dependencies,
    satisfying_packagename = dep[0]
    spectuples = dep[1]
    specstring = ''

    # Catch case where there are new style dependencies among the old....
    if type(spectuples) in [list, tuple]:
      specstring = spectuples_to_specstring(spectuples)
    
    else:
      assert type(spectuples) in [unicode, str], 'Unexpected dep format!'
      specstring = spectuples # It's already a specstring.


    new_deps[distkey].append([satisfying_packagename, specstring])

depdata.dependencies_by_dist = new_deps
depdata.write_data_to_files()





