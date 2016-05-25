"""
<Program>
  test_depdata.py

<Purpose>
  Some unit tests for the depdata module's dependency tools.
  (Can restructure to be more standard later.)

"""

import json
import os

import depresolve # __init__ for errors
import depresolve.depdata as depdata
import testdata


def main():
  """
  """
  test_depdata()

  print("All tests in main() OK")


def test_depdata():
  """
  """
  assert 41 == len(testdata.DEPS_MODERATE), \
      "Set changed: should be len 41 but is len " + \
      str(len(testdata.DEPS_MODERATE)) + " - reconfigure tests"

  json.dump(testdata.DEPS_MODERATE, open('data/test_deps_set.json', 'w'))

  deps = depdata.load_json_db('data/test_deps_set.json')

  assert testdata.DEPS_MODERATE == deps, \
      "JSON write and load via load_json_db is breaking!"


  versions_by_package = depdata.generate_dict_versions_by_package(deps)

  assert 10 == len(versions_by_package) # different package names

  total_package_versions = \
      sum([len(versions_by_package[p]) for p in versions_by_package])
  
  assert 41 == total_package_versions, \
      "Wrong number of versions: " + str(total_package_versions) + "instead" \
      + "of 41."
  
  (edeps, packs_wout_avail_version_info, dists_w_missing_dependencies) = \
      depdata.elaborate_dependencies(deps, versions_by_package)


  # 1 entry in the edeps dict
  assert 41 == len(edeps), \
      "Wrong number of dists in elaborate_dependencies output. " + \
      str(len(edeps)) + "instead of 41."

  # 1 version listed for every possible satisfying dependency
  n_dependencies_elaborated = 0
  for distkey in edeps:
    for satisfying_package_entry in edeps[distkey]:
      list_of_satisfying_versions = satisfying_package_entry[1]
      n_dependencies_elaborated += len(list_of_satisfying_versions)
      #print(distkey + " -> " + str(list_of_satisfying_versions))

  assert 34 == n_dependencies_elaborated, \
      "Expecting 34 satisfying versions (1 for every [depending dist]" + \
      ",[satisfying_version] pair. Instead, got " + \
      str(n_dependencies_elaborated)

  assert depdata.are_deps_valid(testdata.DEPS_MODERATE) and \
      depdata.are_deps_valid(testdata.DEPS_SIMPLE), \
      'The test dependencies are coming up as invalid for some reason....'


  print("test_depdata(): All tests OK.")








if __name__ == '__main__':
  main()



