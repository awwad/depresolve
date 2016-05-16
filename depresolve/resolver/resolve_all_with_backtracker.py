
"""
<Program>
  resolve_all_with_backtracker.py

<Purpose>
  This is a quick script that will try to solve every model 3 dependency
  conflict in the collected conflict data in conflicts_3.json.

  To do this, it will load all dependency data in the elaborated dependency
  format from json fname 'data/elaborated_dependencies.json', then make calls
  to resolvablity.backtracking_satisfy for every model 3 conflict.

  The solution data, parsing (and other) errors, and the unresolvable conflict
  list is all recorded in json files, with occasional early writes to prevent
  loss of all data.

"""


import depresolve
import depresolve.resolver.resolvability as ry
import depresolve.depdata as depdata
import json

def main():

  # Load data, including full elaborated dependencies and conflict model 3 db.
  depdata.ensure_data_loaded(CONFLICT_MODELS=[3], include_edeps=True)

  con3_dists = [dist for dist in depdata.conflicts_3_db if
      depdata.conflicts_3_db[dist]]

  # Solve all the conflicts! (Store data in the filenames listed.)
  # This is very slow.
  ry.resolve_all_via_backtracking(
      con3_dists,
      depdata.elaborated_dependencies,
      depdata.versions_by_package,
      'data/backtracker_solutions.json',
      'data/backtracker_errors.json',
      'data/backtracker_unresolvables.json')


if __name__ == '__main__':
  main()

