"""
<Program>
  test_deptools.py

<Purpose>
  Some unit tests for the dep tools and resolvability assesser.
  (Can restructure to be more standard later.)

"""

import json
import os

import deptools

DEPS_SIMPLE = {
    'X(1)': [  ['B', []], ['C', []]],
    'B(1)': [  ['A', [['>=', '2'], ['<', '4']]]  ],
    'C(1)': [  ['A', [['==', '3']]]  ],
    'A(1)': [],
    'A(2)': [],
    'A(3)': [],
    'A(4)': [],
}

DEPS_MODERATE = {
    'X(1)': [  ['B', []], ['C', []]],
    'B(1)': [  ['A', [['>=', '2'], ['<', '4']]]  ],
    'C(1)': [  ['A', [['==', '3']]]  ],
    'A(1)': [],
    'A(2)': [],
    'A(3)': [],
    'A(4)': [],
    'pip-accel(0.9.10)': [
        ['coloredlogs', [['==', '0.4.3']]],
        ['pip', [['>=', '1.3']]]
    ],
    'autosubmit(3.0.4)': [
        ['six', []],
        ['pyinotify', []]
    ],

    'coloredlogs(0.4.1)': [],
    'coloredlogs(0.4.3)': [],
    'coloredlogs(0.4.6)': [],
    'coloredlogs(0.4.7)': [],
    'coloredlogs(1.0.1)': [  ['humanfriendly', [['>=', '1.25.1']]]  ],
    'coloredlogs(5.0)': [  ['humanfriendly', [['>=', '1.42']]]  ],
    # 'pip(0.2)': [],
    # 'pip(0.2.1)': [],
    # 'pip(0.3.1)': [],
    # 'pip(0.3.dev0)': [],
    # 'pip(0.4)': [],
    # 'pip(0.5)': [],
    # 'pip(0.5.1)': [],
    # 'pip(0.6)': [],
    # 'pip(0.6.1)': [],
    # 'pip(0.6.2)': [],
    # 'pip(0.6.3)': [],
    # 'pip(0.7)': [],
    # 'pip(0.7.1)': [],
    # 'pip(0.7.2)': [],
    # 'pip(0.8)': [],
    # 'pip(0.8.1)': [],
    # 'pip(0.8.2)': [],
    # 'pip(0.8.3)': [],
    # 'pip(1.0)': [],
    # 'pip(1.0.1)': [],
    # 'pip(1.0.2)': [],
    # 'pip(1.1)': [],
    # 'pip(1.2)': [],
    # 'pip(1.2.1)': [],
    # 'pip(1.3)': [],
    # 'pip(1.3.1)': [],
    # 'pip(1.4)': [],
    # 'pip(1.4.1)': [],
    # 'pip(1.5)': [],
    # 'pip(1.5.1)': [],
    # 'pip(1.5.2)': [],
    # 'pip(1.5.3)': [],
    # 'pip(1.5.4)': [],
    # 'pip(1.5.5)': [],
    # 'pip(1.5.6)': [],
    # 'pip(6.0)': [],
    # 'pip(6.0.1)': [],
    # 'pip(6.0.2)': [],
    # 'pip(6.0.3)': [],
    # 'pip(6.0.4)': [],
    # 'pip(6.0.5)': [],
    # 'pip(6.0.6)': [],
    # 'pip(6.0.7)': [],
    # 'pip(6.0.8)': [],
    # 'pip(6.1.0)': [],
    # 'pip(6.1.1)': [],
    # 'pip(7.0.0)': [],
    # 'pip(7.0.1)': [],
    # 'pip(7.0.2)': [],
    # 'pip(7.0.3)': [],
    # 'pip(7.1.0)': [],
    # 'pip(7.1.1)': [],
    # 'pip(7.1.2)': [],
    # 'pip(8.0.0)': [],
    # 'pip(8.0.1)': [],
    # 'pip(8.0.2)': [],
    'six(1.1.0)': [],
    'six(1.2.0)': [],
    'six(1.3.0)': [],
    'six(1.4.0)': [],
    'six(1.4.1)': [],
    'six(1.5.1)': [],
    'six(1.5.2)': [],
    'six(1.6.0)': [],
    'six(1.6.1)': [],
    'six(1.7.0)': [],
    'six(1.7.2)': [],
    'six(1.7.3)': [],
    'six(1.8.0)': [],
    'six(1.9.0)': [],
    'six(1.10.0)': [],
    'pyinotify(0.9.0)': [],
    'pyinotify(0.9.1)': [],
    'pyinotify(0.9.2)': [],
    'pyinotify(0.9.3)': [],
    'pyinotify(0.9.4)': [],
    'pyinotify(0.9.5)': [],
    'pyinotify(0.9.6)': [],
    'humanfriendly(1.27)': [],
    'humanfriendly(1.42)': [],
    'humanfriendly(1.43.1)': [],
    'humanfriendly(1.5)': [],
}





def main():
  """
  """
  test_deptools()

  test_resolver()

  print("Tests successful. (:")




def test_deptools():
  """
  """
  assert 41 == len(DEPS_MODERATE), \
      "Set changed: should be len 41 but is len " + str(len(DEPS_MODERATE)) + \
      " - reconfigure tests"

  json.dump(DEPS_MODERATE, open('test_deps_set.json', 'w'))

  deps = deptools.load_raw_deps_from_json('test_deps_set.json')

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
  deptools.sqli.initialize(db_fname='test_dependencies.db')
  deptools.sqli.delete_all_tables()

  deptools.populate_sql_with_full_dependency_info(
      edeps, versions_by_package, packs_wout_avail_version_info, 
      dists_w_missing_dependencies, db_fname='test_dependencies.db')

  print("test_deptools(): Tests OK.")







def test_resolver():

  import resolvability as ry

  # TEST 1: Test satisfy_immediate_dependencies
  deps = DEPS_SIMPLE
  versions_by_package = deptools.generate_dict_versions_by_package(deps)

  specstring_B1_for_A = '>=2,<4'
  specstring_C1_for_A = '==3'
  specstrings = [specstring_B1_for_A, specstring_C1_for_A,
      '>1',
      '<5',
      '>=1.5',
      ''
  ]

  satisfying_versions = \
      ry.select_satisfying_versions('A', specstrings, versions_by_package)

  expected_result = ['3']
  assert expected_result == satisfying_versions, \
      "Expected one satisfying version: '3'. Got: " + str(satisfying_versions)
  print("test_resolver(): Test 1 OK.")



  # TEST 2: Test strawman_fully_satisfy (during development)
  (edeps, packs_wout_avail_version_info, dists_w_missing_dependencies) = \
      deptools.elaborate_dependencies(deps, versions_by_package)

  satisfying_set = \
      ry.fully_satisfy_strawman1('X(1)', edeps, versions_by_package)

  expected_result = ['A(3)', 'A(3)', 'B(1)', 'C(1)']
  assert expected_result == sorted(satisfying_set), \
      "Expected the strawman solution to X(1)'s dependencies to be " + \
      str(expected_result) + ", sorted, but got instead: " + \
      str(sorted(satisfying_set))
  print("test_resolver(): Test 2 OK.")






if __name__ == '__main__':
  main()
