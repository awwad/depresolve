"""
<Program>
  test_resolvability.py

<Purpose>
  Some unit tests for resolver.resolvability and resolver.depsolver_integrate.
  (Can restructure to be more standard later.)

  Note that some (very large) extra data for these particular tests is at the
  end of the file.

"""
import json

import resolver
import resolver.deptools as deptools

import resolver.resolvability as ry # backtracking solver

from resolver.tests.testdata import *



def main():
  """
  """

  # Should move away from this, but it's a serviceable set of regression tests
  # for now.
  test_old_resolver_suite() 

  # We expected the current version of backtracking_satisfy to fail on the 2nd
  # through 4th calls.
  # Hopefully, it can now work properly. (Nope)

  test_resolver(ry.backtracking_satisfy, DEPS_SIMPLE_SOLUTION, 'X(1)', 
    DEPS_SIMPLE)

  test_resolver(ry.backtracking_satisfy, DEPS_SIMPLE2_SOLUTION, 'X(1)', 
    DEPS_SIMPLE2)#, expected_exception=resolver.UnresolvableConflictError)

  test_resolver(ry.backtracking_satisfy, DEPS_SIMPLE3_SOLUTION, 'X(1)', 
    DEPS_SIMPLE3)#, expected_exception=resolver.UnresolvableConflictError)

  test_resolver(ry.backtracking_satisfy, DEPS_SIMPLE4_SOLUTION, 'X(1)', 
    DEPS_SIMPLE4)#, expected_exception=resolver.UnresolvableConflictError)

  print("Tests successful. (:")



def test_resolver(resolver_func, expected_result, distkey, deps,
    versions_by_package=None, edeps=None, expected_exception=None,
    use_raw_deps=False):
  """
  Returns True if the given resolver produces the expected result on the given
  data, else False.

  Also writes the dependency graph to resolver/output/test_resolver_*.

  Raises UnresolvableConflictError (reraise) if unable to resolve and we were
  not told to expect UnresolvableConflictError. (Same goes for any other
  exceptions)

  If instructed to use raw dependencies (instead of elaborated dependencies),
  will pass deps directly to the named function instead of first elaborating
  the dependencies.

  """

  if versions_by_package is None:
    versions_by_package = deptools.generate_dict_versions_by_package(deps)

  if use_raw_deps:
    edeps = deps

  elif edeps is None:
    (edeps, packs_wout_avail_version_info, dists_w_missing_dependencies) = \
      deptools.elaborate_dependencies(deps, versions_by_package)

  solution = None

  try:
    (solution, _junk_, dotstrings) = \
        resolver_func(distkey, edeps, versions_by_package)

  except Exception as e:
    if expected_exception is None or type(e) is not expected_exception:
      print('Unexpectedly unable to resolve ' + distkey)
      raise
      #return False
    else:
      # We expected this error.
      print('As expected, unable to resolve ' + distkey)
      print('  Exception caught: ' + e.args[0])
      return True

  else:
    print('Resolved ' + distkey + '. Solution: ' + str(solution))
    fobj = open('data/resolver/test_resolver_' + resolver_func.__name__ +
        '_' + distkey + '.dot', 'w')
    fobj.write('digraph G {\n' + dotstrings + '}\n')
    fobj.close()

    if sorted(solution) == sorted(expected_result):
      print('Solution is as expected.')
      return True
    else:
      print('Solution does not match! Expected:')
      print('    Expected: ' + sorted(expected_result))
      print('    Produced: ' + sorted(solution))
      return False








def test_old_resolver_suite():
  res_test1()
  res_test2()
  res_test3()
  res_test4()
  res_test5()
  res_test6()
  res_test7()
  res_test8()
  print("test_resolver_suite(): All resolvability tests OK. (:")


def res_test1():
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



def res_test2():
  deps = DEPS_SIMPLE
  versions_by_package = deptools.generate_dict_versions_by_package(deps)

  # TEST 2: Test fully_satisfy_strawman1 (during development)
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



def res_test3():
  # TEST 3: Detection of model 2 conflicts.
  deps = DEPS_MODEL2
  versions_by_package = deptools.generate_dict_versions_by_package(deps)
  (edeps, packs_wout_avail_version_info, dists_w_missing_dependencies) = \
      deptools.elaborate_dependencies(deps, versions_by_package)
  assert ry.detect_model_2_conflict_from_distkey(
      'motorengine(0.7.4)', edeps, versions_by_package
  ), "Did not detect model 2 conflict for motorengine(0.7.4). ): "
  print("test_resolver(): Test 3 OK.")



def res_test4():
  # TEST 4: Test fully_satisfy_strawman2 (during development)
  deps = DEPS_SIMPLE
  versions_by_package = deptools.generate_dict_versions_by_package(deps)
  (edeps, packs_wout_avail_version_info, dists_w_missing_dependencies) = \
      deptools.elaborate_dependencies(deps, versions_by_package)

  satisfying_set = \
      ry.fully_satisfy_strawman2('X(1)', edeps, versions_by_package)

  expected_result = ['A(3)', 'B(1)', 'C(1)', 'X(1)']
  assert expected_result == sorted(satisfying_set), \
      "Expected the strawman solution to X(1)'s dependencies to be " + \
      str(expected_result) + ", sorted, but got instead: " + \
      str(sorted(satisfying_set))
  print("test_resolver(): Test 4 OK.")



def res_test5():
  # TEST 5: Test fully_satisfy_strawman2 (during development)
  #         on a slightly more complex case.
  deps = DEPS_MODEL2
  versions_by_package = deptools.generate_dict_versions_by_package(deps)
  # (edeps, packs_wout_avail_version_info, dists_w_missing_dependencies) = \
  #     deptools.elaborate_dependencies(deps, versions_by_package)

  edeps = EDEPS_SERIOUS

  satisfying_set = \
      ry.fully_satisfy_strawman2('motorengine(0.7.4)', edeps,
          versions_by_package)

  expected_result = [
      'backports-abc(0.4)',
      'easydict(1.6)',
      'greenlet(0.4.9)',
      'motor(0.1.2)',
      'motorengine(0.7.4)',
      'pymongo(2.5)',
      'six(1.9.0)',
      'tornado(4.3)']
  assert expected_result == sorted(satisfying_set), \
      "Expected the strawman solution to motorengine(0.7.4)'s dependencies " \
      " to be " + str(expected_result) + ", sorted, but got instead: " + \
      str(sorted(satisfying_set))
  print("test_resolver(): Test 5 OK.")


def res_test6():
  # TEST 6: Let's get serious (:
  #con3_json = json.load(open('data/conflicts_3_db.json','r'))
  #dists_w_conflict3 = [p for p in con3_json if con3_json[p]]
  deps = DEPS_SERIOUS
  edeps = EDEPS_SERIOUS
  versions_by_package = deptools.generate_dict_versions_by_package(deps)
  solutions = dict()

  artificial_set = [ # These come from the type 3 conflict results. (:
      'metasort(0.3.6)', 'gerritbot(0.2.0)',
      'exoline(0.2.3)', 'pillowtop(0.1.3)', 'os-collect-config(0.1.8)',
      'openstack-doc-tools(0.21.1)', 'openstack-doc-tools(0.7.1)',
      'python-magnetodbclient(1.0.1)']


  for distkey in artificial_set:
    try:
      solutions[distkey] = \
          ry.fully_satisfy_strawman2(distkey, edeps, versions_by_package)
      print("Resolved: " + distkey)
    except resolver.UnresolvableConflictError:
      solutions[distkey] = -1
      print("Unresolvable: " + distkey)

  print("test_resolver(): Text 6 completed, at least. (:")

  # json.dump(solutions, open('data/resolver/con3_solutions_via_strawman2.json', 'w'))


def res_test7():

  # TEST 7: Test fully_satisfy_backtracking (during development)
  deps = DEPS_SERIOUS
  edeps = EDEPS_SERIOUS
  versions_by_package = deptools.generate_dict_versions_by_package(deps)

  (satisfying_set, _junk_, dotstrings) = \
      ry.backtracking_satisfy('metasort(0.3.6)', edeps, versions_by_package)

  expected_result = [
      'biopython(1.66)', 'metasort(0.3.6)',
      'onecodex(0.0.9)', 'requests(2.5.3)',
      'requests-toolbelt(0.6.0)']

  assert expected_result == sorted(satisfying_set), \
      "Expected the strawman3 solution to metasort(0.3.6)'s dependencies " \
      " to be " + str(expected_result) + ", sorted, but got instead: " + \
      str(sorted(satisfying_set))
  
  print("test_resolver(): Test 7 OK. (:")




def res_test8():
  deps = DEPS_SERIOUS
  edeps = EDEPS_SERIOUS
  versions_by_package = VERSIONS_BY_PACKAGE

  # "TEST" 8: Try test 6 with fully_satisfy_backtracking instead to compare.
  # Expect these conflicts to resolve.
  #con3_json = json.load(open('data/conflicts_3_db.json','r'))
  #dists_w_conflict3 = [p for p in con3_json if con3_json[p]]
  solutions = dict()
  dotstrings = dict()

  artificial_set = [ # These come from the type 3 conflict results. (:
      'metasort(0.3.6)',
      'pillowtop(0.1.3)',
      'os-collect-config(0.1.8)',
      'openstack-doc-tools(0.7.1)',
      'python-magnetodbclient(1.0.1)']


  for distkey in artificial_set:
    try:
      (solutions[distkey], _junk_, dotstrings[distkey]) = \
          ry.backtracking_satisfy(distkey, edeps, versions_by_package)
      print('Resolved: ' + distkey)
    except resolver.UnresolvableConflictError:
      solutions[distkey] = -1
      dotstrings[distkey] = ''
      print('Unresolvable: ' + distkey)

  n_unresolvable = len(
      [distkey for distkey in solutions if solutions[distkey] == -1])

  fobj = open('data/resolver/test8_solutions_via_strawman3.json', 'w')
  json.dump(solutions, fobj)
  fobj.close()

  # Write the dot graphs.
  for distkey in artificial_set:
    fobj = open('data/resolver/test8_dotgraph_' + distkey + '.dot', 'w')
    fobj.write('digraph G {\n')
    fobj.write(dotstrings[distkey])
    fobj.write('}\n')
    fobj.close()


  assert 0 == n_unresolvable, 'Expect 0 unresolvable conflicts. Got ' + \
      str(n_unresolvable) + ' instead. ):'

  fobj = open('data/resolver/test8_solutions_via_backtracking.json', 'w')
  json.dump(solutions, fobj)
  fobj.close()

  print("test_resolver(): Test 8 OK (: (: (:")



def res_test9():
  # "TEST" 9: Try to resolve a conflict we know to be unresolvable.
  deps = DEPS_SERIOUS
  edeps = EDEPS_SERIOUS
  versions_by_package = VERSIONS_BY_PACKAGE
  solutions = dict()
  dotstrings = dict()

  artificial_set = [ # These come from the type 3 conflict results. (:
      'gerritbot(0.2.0)',
      'exoline(0.2.3)',
      'openstack-doc-tools(0.21.1)']

  for distkey in artificial_set:
    try:
      (solutions[distkey], _junk_, dotstrings[distkey]) = \
          ry.backtracking_satisfy(distkey, edeps, versions_by_package)
      print('Resolved: ' + distkey)
    except resolver.UnresolvableConflictError:
      solutions[distkey] = -1
      dotstrings[distkey] = ''
      print('Unresolvable: ' + distkey)

  n_unresolvable = len(
      [distkey for distkey in solutions if solutions[distkey] == -1])

  fobj = open('data/resolver/test9_solutions_via_backtracking.json', 'w')
  json.dump(solutions, fobj)
  fobj.close()

  # Write the dot graphs.
  for distkey in artificial_set:
    fobj = open('data/resolver/test9_dotgraph_' + distkey + '.dot', 'w')
    fobj.write('digraph G {\n')
    fobj.write(dotstrings[distkey])
    fobj.write('}\n')
    fobj.close()


  assert 0 == n_unresolvable, 'Expect 3 unresolvable conflicts. Got ' + \
      str(n_unresolvable) + ' instead. ):'

  print("test_resolver(): Test 9 OK. (:")







# Auxiliary test data (very large)

DEPS_SERIOUS = deptools.load_raw_deps_from_json('data/dependencies_db.json')
EDEPS_SERIOUS = json.load(open('data/elaborated_dependencies.json', 'r'))
VERSIONS_BY_PACKAGE = deptools.generate_dict_versions_by_package(DEPS_SERIOUS)

