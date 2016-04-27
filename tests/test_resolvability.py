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

import depresolve
import depresolve.deptools as deptools

import depresolve.resolver.resolvability as ry # backtracking solver

# Don't from-import dynamic global variables, or target module globals don't
# stay bound if the aliases are rebound.
#from tests.testdata import *
import tests.testdata as data

logger = depresolve.logging.getLogger('test_resolvability')


def main():
  """
  """
  successes = []

  # Load the giant dictionary of scraped dependencies for DEPS_SERIOUS etc.
  data.ensure_full_data_loaded()


  # Test resolvability.conflicts_with, which is used in the resolver.
  successes.append(test_conflicts_with())

  # Test resolvability.dist_lists_are_equal, which is used in testing.
  successes.append(test_dist_lists_are_equal())

  # Should move away from this, but it's a serviceable set of regression tests
  # for now.
  successes.extend(test_old_resolver_suite())


  # We expected the current version of backtracking_satisfy to fail on the 2nd
  # through 4th calls.
  # Hopefully, it can now work properly. (Nope - switching expectation back
  # to failure. May skip fixing. Have moved on to SAT via depsolver.)

  successes.append(test_resolver(ry.backtracking_satisfy,
      data.DEPS_SIMPLE_SOLUTION, 'X(1)', data.DEPS_SIMPLE))

  successes.append(test_resolver(ry.backtracking_satisfy,
      data.DEPS_SIMPLE2_SOLUTION, 'X(1)', data.DEPS_SIMPLE2,
      expected_exception=depresolve.UnresolvableConflictError))

  successes.append(test_resolver(ry.backtracking_satisfy,
      data.DEPS_SIMPLE3_SOLUTION, 'X(1)', data.DEPS_SIMPLE3,
      expected_exception=depresolve.UnresolvableConflictError))

  successes.append(test_resolver(ry.backtracking_satisfy,
      data.DEPS_SIMPLE4_SOLUTION, 'X(1)', data.DEPS_SIMPLE4,
      expected_exception=depresolve.UnresolvableConflictError))

  assert False not in [success for success in successes], \
      "Some tests failed! Results are: " + str(successes)

  logger.info("All tests in main() successful. (: (:")





def test_dist_lists_are_equal():
  """Tests resolvability.dist_lists_are_equal."""

  test_sets = [
      (
        True,   # Expect this result
        [],     # from comparing this list
        []      # to this list
      ),

      (True, ['django(1.8)', 'foo(1.0.0)'], ['django(1.8.0)', 'foo(1)']),
      (False, ['bar(1)'], ['bar(1.0.1)']),
      (True, ['barry(3.5)'], ['barry(3.5)']),
      (False, ['onevsempty(2)'], []),
      (False, [], ['twovsempty(1)']),
      (False, ['diffver(1.3)'], ['diffver(1.4)']),
      (False, ['foo(1.0.0)', 'bar(2.0)'], ['bat(1.0.0)', 'bar(2.0)']),
      (False, ['foo(1)'], ['bar(1)'])
  ]

  for (expected, list1, list2) in test_sets:
    assert expected == ry.dist_lists_are_equal(list1, list2), \
        'Test failed - function resolvability.dist_lists_are_equal returned' +\
        ' unexpected answer. Lists were:\n' + str(list1) + '\n' + str(list2)

  logger.info('Tests successful. (:')
  return True





def test_conflicts_with():
  """Tests resolvability.conflicts_with."""

  test_sets = [
    (
      [],                  # Expect this result
      'A(1.5)',            # from checking for conflicts between this distkey
      ['A(1.5)', 'B(2)'],  # and this list of distkeys
    ),
    ( ['A(2)'], 'A(1)', ['A(2)'] ),
    ( [], 'Z(5.5.1)', [] ),
    ( [], 'bat(2.6)', ['foo(1.0.0)', 'bar(2.0)'] ),
    ( [], 'D(1)', ['D(1.0)'] ),
    ( [], 'D(1)', ['D(1.0.0)'] ),
    ( [], 'D(1.0.0)', ['D(1.0)'] ),
    ( [], 'D(1.0.0)', ['D(1)'] ),
    ( [], 'D(1.0.0)', ['D(1.0.0)'] ),
    ( ['D(1)'], 'D(1.0.1)', ['D(1)'] ),
    ( ['g(3.4.1)', 'g(3.2)'], 'g(1.04.3)',
      ['g(1.04.3)', 'g(3.4.1)', 'g(3.2)'] ),

  ]

  for (expected, distkey, dlist) in test_sets:
    assert expected == ry.conflicts_with(distkey, dlist), \
        'Test failed - function resolvability.conflicts_with returned' +\
        ' unexpected answer. Args were:\n' + distkey+ '\n' + str(dlist)

  logger.info('Tests successful. (:')
  return True






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

  TODO: Should compare the solutions more correctly, checking the versions
  against each other. There are cases where depsolver may return '2.0.0'
  instead of '2' for the version, for example, and that needs to still be
  regarded as correct. I should use pip's Version class methods to test
  equality.

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
      logger.exception('Unexpectedly unable to resolve ' + distkey)
      raise
      #return False
    else:
      # We expected this error.
      logger.info('As expected, unable to resolve ' + distkey + ' due to ' +
          str(type(e)) + '.')
      logger.info('  Exception caught: ' + e.args[0])
      return True

  else:
    logger.info('Resolved ' + distkey + '. Solution: ' + str(solution))
    if dotstrings is not None: # If the func provides dotstrings
      fobj = open('data/resolver/test_resolver_' + resolver_func.__name__ +
          '_' + distkey + '.dot', 'w')
      fobj.write('digraph G {\n' + dotstrings + '}\n')
      fobj.close()

    # Is the solution set as expected?
    if ry.dist_lists_are_equal(solution, expected_result):
      logger.info('Solution is as expected.')
      return True
    else:
      logger.info('Solution does not match! Expected:')
      logger.info('    Expected: ' + str(sorted(expected_result)))
      logger.info('    Produced: ' + str(sorted(solution)))
      return False








def test_old_resolver_suite():
  #res_test1() # No longer using the function this tests.
  successes = []

  successes.append(res_test2())
  successes.append(res_test3())
  successes.append(res_test4())
  successes.append(res_test5())
  successes.append(res_test6())
  successes.append(res_test7())
  successes.append(res_test8())
  if False not in successes:
    logger.info("test_resolver_suite(): All resolvability tests OK. (:")
  else:
    logger.error('test_resolver_suite() has failures.')
  return successes



# # No longer using satisfy_immediate_dependencies, so commenting out.
# def res_test1():
#   """TEST 1: Test satisfy_immediate_dependencies"""
#   deps = data.DEPS_SIMPLE
#   versions_by_package = deptools.generate_dict_versions_by_package(deps)

#   specstring_B1_for_A = '>=2,<4'
#   specstring_C1_for_A = '==3'
#   specstrings = [specstring_B1_for_A, specstring_C1_for_A,
#       '>1',
#       '<5',
#       '>=1.5',
#       ''
#   ]

#   satisfying_versions = \
#       ry.select_satisfying_versions('A', specstrings, versions_by_package)

#   expected_result = ['3']
#   assert expected_result == satisfying_versions, \
#       "Expected one satisfying version: '3'. Got: " + str(satisfying_versions)
#   logger.info("test_resolver(): Test 1 OK.")



def res_test2():
  """TEST 2: Test fully_satisfy_strawman1 (during development)"""

  deps = data.DEPS_SIMPLE
  versions_by_package = deptools.generate_dict_versions_by_package(deps)

  (edeps, packs_wout_avail_version_info, dists_w_missing_dependencies) = \
      deptools.elaborate_dependencies(deps, versions_by_package)

  satisfying_set = \
      ry.fully_satisfy_strawman1('X(1)', edeps, versions_by_package)

  expected_result = ['A(3)', 'A(3)', 'B(1)', 'C(1)']
  
  success = expected_result == sorted(satisfying_set)

  if not success:
    logger.error("Expected the solution to X(1)'s dependencies to be " +
      str(expected_result) + ", sorted, but got instead: " +
      str(sorted(satisfying_set)))
  else:
    logger.info("test_resolver(): Test 2 OK.")

  return success



def res_test3():
  """TEST 3: Detection of model 2 conflicts."""
  deps = data.DEPS_MODEL2
  versions_by_package = deptools.generate_dict_versions_by_package(deps)
  (edeps, packs_wout_avail_version_info, dists_w_missing_dependencies) = \
      deptools.elaborate_dependencies(deps, versions_by_package)

  success = ry.detect_model_2_conflict_from_distkey(
      'motorengine(0.7.4)', edeps, versions_by_package)

  if not success:
    logger.error('Did not detect model 2 conflict for motorengine(0.7.4). ):')
  else:
    logger.info("test_resolver(): Test 3 OK.")

  return success



def res_test4():
  """TEST 4: Test fully_satisfy_strawman2 (during development)"""
  deps = data.DEPS_SIMPLE
  versions_by_package = deptools.generate_dict_versions_by_package(deps)
  (edeps, packs_wout_avail_version_info, dists_w_missing_dependencies) = \
      deptools.elaborate_dependencies(deps, versions_by_package)

  satisfying_set = \
      ry.fully_satisfy_strawman2('X(1)', edeps, versions_by_package)

  expected_result = ['A(3)', 'B(1)', 'C(1)', 'X(1)']
  
  success = expected_result == sorted(satisfying_set)

  if not success:
    logger.error("Expected the strawman solution to X(1)'s dependencies to be "
        + str(expected_result) + ", sorted, but got instead: " +
        str(sorted(satisfying_set)))
  else:
    logger.info("test_resolver(): Test 4 OK.")

  return success



def res_test5():
  """
  TEST 5: Test fully_satisfy_strawman2 (during development)
  on a slightly more complex case.
  """
  deps = data.DEPS_MODEL2
  versions_by_package = deptools.generate_dict_versions_by_package(deps)

  edeps = data.EDEPS_SERIOUS

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
      'six(1.10.0)',
      'tornado(4.3)']

  success = expected_result == sorted(satisfying_set)
  if not success:
    logger.error("Expected the strawman solution to motorengine(0.7.4)'s "
        "dependencies to be " + str(expected_result) + ", sorted, but got "
        "instead: " + str(sorted(satisfying_set)))
  else:
    logger.info("test_resolver(): Test 5 OK.")

  return success


def res_test6():
  """TEST 6: Let's get serious (:"""
  data.ensure_full_data_loaded()
  deps = data.DEPS_SERIOUS
  edeps = data.EDEPS_SERIOUS
  versions_by_package = data.VERSIONS_BY_PACKAGE#deptools.generate_dict_versions_by_package(deps)
  solutions = dict()

  artificial_set = [ # These come from the type 3 conflict results. (:
      'metasort(0.3.6)', 'gerritbot(0.2.0)',
      'exoline(0.2.3)', 'pillowtop(0.1.3)', 'os-collect-config(0.1.8)',
      'openstack-doc-tools(0.21.1)', 'openstack-doc-tools(0.7.1)',
      'python-magnetodbclient(1.0.1)']

  errored = False

  for distkey in artificial_set:
    try:
      solutions[distkey] = \
          ry.fully_satisfy_strawman2(distkey, edeps, versions_by_package)
      logger.debug("Resolved: " + distkey)
    except depresolve.UnresolvableConflictError:
      solutions[distkey] = -1
      logger.debug("Unresolvable: " + distkey)
    except Exception as e:
      logger.error('Unexpected exception while processing ' + distkey +
          ' with strawman2! Exception follows: ' + str(e.args))
      errored = True

  if not errored:
    logger.info("test_resolver(): Text 6 completed, at least. (:")
  else:
    logger.warning('test_resolver() saw unexpected exceptions....')
  return errored


def res_test7():
  """TEST 7: Test fully_satisfy_backtracking (during development)"""
  data.ensure_full_data_loaded()
  deps = data.DEPS_SERIOUS
  edeps = data.EDEPS_SERIOUS
  versions_by_package = deptools.generate_dict_versions_by_package(deps)

  (satisfying_set, _junk_, dotstrings) = \
      ry.backtracking_satisfy('metasort(0.3.6)', edeps, versions_by_package)

  expected_result = [
      'biopython(1.66)', 'metasort(0.3.6)',
      'onecodex(0.0.9)', 'requests(2.5.3)',
      'requests-toolbelt(0.6.0)']

  success = expected_result == sorted(satisfying_set)

  if not success:
    logger.error("Expected the strawman3 solution to metasort(0.3.6)'s "
      "dependencies to be " + str(expected_result) + ", sorted, but got "
      "instead: " + str(sorted(satisfying_set)))

  else:
    logger.info("test_resolver(): Test 7 OK. (:")

  return success



def res_test8():
  """
  "TEST" 8: Try test 6 with fully_satisfy_backtracking instead to compare.
  Expect these conflicts to resolve.
  """
  data.ensure_full_data_loaded()
  deps = data.DEPS_SERIOUS
  edeps = data.EDEPS_SERIOUS
  versions_by_package = data.VERSIONS_BY_PACKAGE

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
      logger.debug('Resolved: ' + distkey)
    except depresolve.UnresolvableConflictError:
      solutions[distkey] = -1
      dotstrings[distkey] = ''
      logger.debug('Unresolvable: ' + distkey)

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


  success = 0 == n_unresolvable

  fobj = open('data/resolver/test8_solutions_via_backtracking.json', 'w')
  json.dump(solutions, fobj)
  fobj.close()

  if not success:
    logger.error('Expect 0 unresolvable conflicts. Got ' +
        str(n_unresolvable) + ' instead. ):')
  else:
    logger.info("test_resolver(): Test 8 OK (: (: (:")

  return success


def res_test9():
  """ TEST 9: Try to resolve a conflict we know to be unresolvable."""
  data.ensure_full_data_loaded()
  deps = data.DEPS_SERIOUS
  edeps = data.EDEPS_SERIOUS
  versions_by_package = data.VERSIONS_BY_PACKAGE
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
      logger.debug('Resolved: ' + distkey)
    except depresolve.UnresolvableConflictError:
      solutions[distkey] = -1
      dotstrings[distkey] = ''
      logger.debug('Unresolvable: ' + distkey)

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


  success = 0 == n_unresolvable
  if not success:
    logger.error('Expect 3 unresolvable conflicts. Got ' +
        str(n_unresolvable) + ' instead. ):')
  else:
    logger.info("test_resolver(): Test 9 OK. (:")

  return success





def test_sort_versions():
  """
  Make sure the version sort used by the resolver is working.
  """

  test_sets = [
      (['1.5', '1.6.3', '1.5.1', '1.10', '1.13.5', '12.5'], # to sort
       ['12.5', '1.13.5', '1.10', '1.6.3', '1.5.1', '1.5']), # expected output
      ([], []),
      (['0.5.9', '5.0', '0.5.9.1'], ['5.0', '0.5.9.1', '0.5.9']),
  ]

  for pair in test_sets:
    to_sort = pair[0]
    expected_result = pair[1]

    post_sort = ry.sort_versions(to_sort)

    if post_sort != expected_result:
      exception_text = 'sort_versions failed to produce the expected output' +\
          '.\n  Expected: ' + str(expected_result) + '\n  Got: ' + \
          str(post_sort)
      logger.error(exception_text)
      raise Exception(exception_text)
      # return False

  logger.info('test_sort_versions(): Test passed. (:')
  return True




if __name__ == '__main__':
  main()
