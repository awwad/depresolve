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
import depresolve.depdata as depdata

import depresolve.resolver.resolvability as ry # backtracking solver

# Don't from-import dynamic global variables, or target module globals don't
# stay bound if the aliases are rebound.
#from tests.testdata import *
import testdata

# for acceptable nested exception traceback handling on python 2 & 3:
import six, sys

logger = depresolve.logging.getLogger('test_resolvability')


class UnexpectedException(Exception):
  pass


def main():
  """
  """
  successes = []

  # Load the giant dictionary of scraped dependencies for heavy testing.
  depdata.ensure_data_loaded(include_edeps=True)

  # Test resolvability.conflicts_with, which is used in the resolver.
  successes.append(test_conflicts_with()) #0

  # Test resolvability.dist_lists_are_equal, which is used in testing.
  successes.append(test_dist_lists_are_equal()) #1

  # Test resolvability.sort_versions, which is used in a variety of functions.
  successes.append(test_sort_versions()) #2

  # Test the detection of model 2 conflicts from deps.
  successes.append(test_detect_model_2_conflicts) #3


  # Test the backtracking resolver on basic samples.
  # We expected the current version of backtracking_satisfy to fail on the 2nd
  # through 4th calls.
  # Hopefully, it can now work properly. (Nope - switching expectation back
  # to failure. New backtracking algorithm will handle these, later.)

  successes.append(test_resolver(ry.backtracking_satisfy,
      testdata.DEPS_SIMPLE_SOLUTION, 'x(1)', testdata.DEPS_SIMPLE)) #4

  successes.append(test_resolver(ry.backtracking_satisfy,
      testdata.DEPS_SIMPLE2_SOLUTION, 'x(1)', testdata.DEPS_SIMPLE2,
      expected_exception=depresolve.UnresolvableConflictError)) #5

  successes.append(test_resolver(ry.backtracking_satisfy,
      testdata.DEPS_SIMPLE3_SOLUTION, 'x(1)', testdata.DEPS_SIMPLE3,
      expected_exception=depresolve.UnresolvableConflictError)) #6

  successes.append(test_resolver(ry.backtracking_satisfy,
      testdata.DEPS_SIMPLE4_SOLUTION, 'x(1)', testdata.DEPS_SIMPLE4,
      expected_exception=depresolve.UnresolvableConflictError)) #7


  # Test the backtracking resolver on the case of metasort(0.3.6)
  expected_metasort_result = [
      'biopython(1.66)', 'metasort(0.3.6)', 'onecodex(0.0.9)',
      'requests(2.5.3)', 'requests-toolbelt(0.6.0)']
  successes.append(test_resolver(ry.backtracking_satisfy, #8
      expected_metasort_result, 'metasort(0.3.6)',
      depdata.dependencies_by_dist, 
      versions_by_package=depdata.versions_by_package,
      edeps=depdata.elaborated_dependencies))


  # Test the backtracking resolver on a few model 3 conflicts (pip
  # failures). Expect these conflicts to resolve. Formerly test 8. #9-13
  for distkey in testdata.CONFLICT_MODEL_3_SAMPLES:
    successes.append(test_resolver(ry.backtracking_satisfy, None, distkey,
        depdata.dependencies_by_dist,
        versions_by_package=depdata.versions_by_package,
        edeps=depdata.elaborated_dependencies))


  # Test the backtracking resolver on some conflicts we know to be
  # unresolvable. Formerly test 9. #14-16
  for distkey in testdata.UNRESOLVABLE_SAMPLES:
    successes.append(test_resolver(ry.backtracking_satisfy, None, distkey,
        depdata.dependencies_by_dist,
        versions_by_package=depdata.versions_by_package,
        edeps=depdata.elaborated_dependencies,
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
      'a(1.5)',            # from checking for conflicts between this distkey
      ['a(1.5)', 'b(2)'],  # and this list of distkeys
    ),
    ( ['a(2)'], 'a(1)', ['a(2)'] ),
    ( [], 'z(5.5.1)', [] ),
    ( [], 'bat(2.6)', ['foo(1.0.0)', 'bar(2.0)'] ),
    ( [], 'd(1)', ['d(1.0)'] ),
    ( [], 'd(1)', ['d(1.0.0)'] ),
    ( [], 'd(1.0.0)', ['d(1.0)'] ),
    ( [], 'd(1.0.0)', ['d(1)'] ),
    ( [], 'd(1.0.0)', ['d(1.0.0)'] ),
    ( ['d(1)'], 'd(1.0.1)', ['d(1)'] ),
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
  Returns True if the given resolver function returns the expected result on
  the given data, else False. More modes described in args notes below.

  Solutions are compared with intelligent version parsing outsourced partly to
  pip's pip._vendor.packaging.version classes. For example, 2.0 and 2 and 2.0.0
  are all treated as equivalent.


  Arguments:

    resolver_func
      Argument resolver_func should be a function that accepts 3 arguments and
      returns a solution list:
        - Arg 1:  distkey to generate an install set for, whose installation
                  results in a fully satisfied set of dependencies
        - Arg 2:  dependency data (either deps or edeps, per depdata.py)
        - Arg 3:  versions_by_package, a dict mapping package names to all
                  versions of that package available
        - Return: a list containing the distkeys for dists to install

    expected_result
      This should be a list of distkeys. If the list given matches the solution
      generated by calling resolver_func with the appropriate arguments, we
      return True.
      If this is None, then we don't care what solution is returned by the call
      to resolver_func, only that no unexpected exceptions were raised and
      any expected exception was raised.

    distkey
      The distkey of the distribution to solve for (find install set that
      fully satisfies).
    
    deps
      Dependency data to be used in resolution.


  Optional Arguments:
    
    versions_by_package
      As described elsewhere, the dictionary mapping package names to available
      versions of those packages. If not provided, this is generated from deps.

    use_raw_deps
      If True, we do not try to elaborate dependencies (or use provided
      elaborated dependencies), instead passing the deps provided on in our
      call to resolver_func. Some resolvers do not use elaborated dependencies.

    edeps
      If provided, we don't elaborate the deps argument, but instead use these.

    expected_exception
      The type() of an exception that we expect to receive. If provided, we
      disregard expected_result and instead expect to catch an exception of the
      indicated type, returning True if we catch one and False otherwise.


  Raises:

    - UnresolvableConflictError (reraise) if unable to resolve and we were not
      told to expect UnresolvableConflictError. (Same goes for any other
      exceptions generated by call to resolver_func.)

  Side Effects:
    (NO:
     Used to also write dependency graph to resolver/output/test_resolver_* in
     graphviz .dot format, but have turned this off for now.)

  """

  if versions_by_package is None:
    versions_by_package = depdata.generate_dict_versions_by_package(deps)

  if use_raw_deps:
    edeps = deps

  elif edeps is None:
    (edeps, packs_wout_avail_version_info, dists_w_missing_dependencies) = \
      depdata.elaborate_dependencies(deps, versions_by_package)

  solution = None

  try:
    #(solution, _junk_, dotstrings) = \
    solution = \
        resolver_func(distkey, edeps, versions_by_package)

  except Exception as e:
    if expected_exception is None or type(e) is not expected_exception:
      logger.exception('Test Failure: Unexpectedly unable to resolve ' +
          distkey)

      # Compromise traceback style so as not to give up python2 compatibility.
      six.reraise(UnexpectedException, UnexpectedException('Unexpectedly '
          'unable to resolve ' + distkey), sys.exc_info()[2])

      # Python 3 style (by far the nicest):
      #raise UnexpectedException('Unexpectedly unable to resolve ' + distkey) \
      #    from e

      # Original (2 or 3 compatible but not great on either, especially not 2)
      #raise

      #return False

    else:
      # We expected this error.
      logger.info('As expected, unable to resolve ' + distkey + ' due to ' +
          str(type(e)) + '.')
      logger.info('  Exception caught: ' + e.args[0])
      return True

  else:
    logger.info('Resolved ' + distkey + '. Solution: ' + str(solution))
    #if dotstrings is not None: # If the func provides dotstrings
    #  fobj = open('data/resolver/test_resolver_' + resolver_func.__name__ +
    #      '_' + distkey + '.dot', 'w')
    #  fobj.write('digraph G {\n' + dotstrings + '}\n')
    #  fobj.close()

    # Were we expecting an exception? (We didn't get one if we're here.)
    if expected_exception is not None:
      logger.info('Expecting exception (' + str(expected_exception) + ') but '
          'none were raised.')
      return False

    # If expected_result is None, then we didn't care what the result was as
    # long as there was no unexpected exception / as long as whatever exception
    # is expected was raised.
    elif expected_result is None:
      logger.info('No particular solution expected and resolver call did not '
          'raise an exception, therefore result is acceptable.')
      return True

    # Is the solution set as expected?
    elif ry.dist_lists_are_equal(solution, expected_result):
      logger.info('Solution is as expected.')
      return True

    else:
      logger.info('Solution does not match! Expected:')
      logger.info('    Expected: ' + str(sorted(expected_result)))
      logger.info('    Produced: ' + str(sorted(solution)))
      return False





def test_detect_model_2_conflicts():
  """TEST 3: Detection of model 2 conflicts."""
  deps = testdata.DEPS_MODEL2
  versions_by_package = depdata.generate_dict_versions_by_package(deps)
  (edeps, packs_wout_avail_version_info, dists_w_missing_dependencies) = \
      depdata.elaborate_dependencies(deps, versions_by_package)

  success = ry.detect_model_2_conflict_from_distkey(
      'motorengine(0.7.4)', edeps, versions_by_package)

  if not success:
    logger.error('Did not detect model 2 conflict for motorengine(0.7.4). ):')
  else:
    logger.info("test_resolver(): Test 3 OK.")

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
