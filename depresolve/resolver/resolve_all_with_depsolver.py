
"""
<Program>
  resolve_all_with_depsolver.py

<Purpose>
  This is a quick script that will try to solve every model 3 dependency
  conflict in the collected conflict data in conflicts_3.json.

  To do this, it will load all package info previously converted for depsolver
  json fname 'data/deps_converted_for_depsolver.json', then make calls to
  depsolver_integrate.resolve_via_depsolver() for every model 3 conflict.

  enthought/depsolver is used by the depsolver_integrate module. It's a
  full-python SAT solver intended for package dependencies resolution.

  The solution data, parsing (and other) errors, and the unresolvable conflict
  list is all recorded in json files, with occasional early writes to prevent
  loss of all data.

  (I've now integrated most of the content of the script into the
  depsolver_integrate module itself, though that code should still be
  polished, certainly.)

"""


import depresolve
import depresolve.resolver.depsolver_integrate as di
import json

def main():

  # Get the model 3 conflict data. (:
  con3_data = json.load(open('data/conflicts_3.json', 'r'))

  # All dists with model 3 conflicts.
  con3_dists = [dist for dist in con3_data if con3_data[dist]]

  # Reload the package information formatted for depsolver.
  pinfos = di.reload_already_converted_from_json(
      'data/deps_converted_for_depsolver.json')


  # Solve all the conflicts!
  # This is very, VERY slow.
  di.resolve_all_via_depsolver(
      con3_dists,
      pinfos,
      'data/depsolver_solutions.json',
      'data/depsolver_errors.json',
      'data/depsolver_unresolvables.json')


if __name__ == '__main__':
  main()

