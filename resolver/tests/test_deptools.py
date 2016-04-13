"""
<Program>
  test_deptools.py

<Purpose>
  Some unit tests for the dep tools and resolvability assesser.
  (Can restructure to be more standard later.)

"""

import json
import os

import resolver # __init__ for errors

import resolver.deptools as deptools

from resolver.tests.testdata import *


def main():
  """
  """
  test_deptools()

  print("Tests successful. (:")


def test_deptools():
  """
  """
  assert 41 == len(DEPS_MODERATE), \
      "Set changed: should be len 41 but is len " + str(len(DEPS_MODERATE)) + \
      " - reconfigure tests"

  json.dump(DEPS_MODERATE, open('data/test_deps_set.json', 'w'))

  deps = deptools.load_raw_deps_from_json('data/test_deps_set.json')

  assert DEPS_MODERATE == deps, \
      "JSON write and load via load_raw_deps_from_json is breaking!"


  versions_by_package = deptools.generate_dict_versions_by_package(deps)

  assert 10 == len(versions_by_package) # different package names

  total_package_versions = \
      sum([len(versions_by_package[p]) for p in versions_by_package])
  
  assert 41 == total_package_versions, \
      "Wrong number of versions: " + str(total_package_versions) + "instead" \
      + "of 41."
  
  (edeps, packs_wout_avail_version_info, dists_w_missing_dependencies) = \
      deptools.elaborate_dependencies(deps, versions_by_package)

  #print(str(len(edeps)))
  from pprint import pprint
  #pprint(edeps)

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


  # Clear any pre-existing test database.
  deptools.sqli.initialize(db_fname='data/test_dependencies.db')
  deptools.sqli.delete_all_tables()

  deptools.populate_sql_with_full_dependency_info(
      edeps, versions_by_package, packs_wout_avail_version_info, 
      dists_w_missing_dependencies, db_fname='data/test_dependencies.db')

  print("test_deptools(): Tests OK.")








if __name__ == '__main__':
  main()



