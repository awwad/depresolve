
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
import depresolve.deptools as deptools
import json

def main():

  # Get the model 3 conflict data. (:
  con3_data = json.load(open('data/conflicts_3.json', 'r'))

  # All dists with model 3 conflicts.
  con3_dists = [dist for dist in con3_data if con3_data[dist]]

  # Reload the package information formatted for depsolver.
  edeps = json.load(open('data/elaborated_dependencies.json', 'r'))

  versions_by_package = deptools.generate_dict_versions_by_package(edeps)


  # Solve all the conflicts!
  # This is very slow.
  ry.resolve_all_via_backtracking(
      con3_dists,
      edeps,
      versions_by_package,
      'data/backtracker_solutions.json',
      'data/backtracker_errors.json',
      'data/backtracker_unresolvables.json')


if __name__ == '__main__':
  main()

