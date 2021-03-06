"""
<Program>
  test_resolvability.py

<Purpose>
  Some unit tests for resolver.resolvability and resolver.depsolver_integrate.
  (Can restructure to be more standard later.)

  Note that some extra data for the tests is at the end.

"""
import depresolve
logger = depresolve.logging.getLogger('depresolve')
import depresolve.depdata as depdata
import depresolve.resolver.resolvability as resolvability
import test_resolvability

import depresolve.resolver.depsolver_integrate as depsolver_integrate # SAT solver

# Don't from-import, or target module globals don't stay bound if the aliases
# are rebound.
#from tests.testdata import *
import testdata


def main():

  # Try out the SAT solver in depsolver by using the wrapper function in
  # depsolver_integrate and passing that to the resolver tester in
  # resolver.test_resolvability.
  successes = []

  # Does the version string conversion work as expected?
  successes.append(test_depsolver_version_str_conversion())

  # Can we convert basic dependencies into depsolver PackageInfo?
  successes.append(test_depsolver_conversion())

  # Can we convert slightly more elaborate dependencies into depsolver
  # PackageInfo?
  successes.append(test_depsolver_conversion2())
  successes.append(test_depsolver_conversion3())


  # Basic resolvability test.
  successes.append(test_resolvability.test_resolver(
      depsolver_integrate.resolve_via_depsolver, # resolver function
      testdata.DEPS_SIMPLE_SOLUTION, #expected result
      'x(1)', # dist to install
      testdata.DEPS_SIMPLE, # dependency data
      use_raw_deps=True # Do not convert deps to edeps - func expects deps.
  ))


  # The next three test resolvable conflicts that my backtracker can't solve.
  successes.append(test_resolvability.test_resolver(
      depsolver_integrate.resolve_via_depsolver, # resolver function
      testdata.DEPS_SIMPLE2_SOLUTION, #expected result
      'x(1)', # dist to install
      testdata.DEPS_SIMPLE2, # dependency data
      use_raw_deps=True # Do not convert deps to edeps - func expects deps.
  ))

  successes.append(test_resolvability.test_resolver(
      depsolver_integrate.resolve_via_depsolver, # resolver function
      testdata.DEPS_SIMPLE3_SOLUTION, #expected result
      'x(1)', # dist to install
      testdata.DEPS_SIMPLE3, # dependency data
      use_raw_deps=True # Do not convert deps to edeps - func expects deps.
  ))

  successes.append(test_resolvability.test_resolver(
      depsolver_integrate.resolve_via_depsolver, # resolver function
      testdata.DEPS_SIMPLE4_SOLUTION, #expected result
      'x(1)', # dist to install
      testdata.DEPS_SIMPLE4, # dependency data
      use_raw_deps=True # Do not convert deps to edeps - func expects deps.
  ))

  # This tests a SLIGHTLY more complex version string, via the resolver.
  successes.append(test_resolvability.test_resolver(
      depsolver_integrate.resolve_via_depsolver, # resolver function
      DEPS_EDGE_CASES_SOLUTION, #expected result
      'pip-accel(0.9.10)', # dist to install
      DEPS_EDGE_CASES, # dependency data
      use_raw_deps=True # Do not convert deps to edeps - func expects deps.
  ))


  # # The next two test complex versions strings and are otherwise the same as 2.
  # successes.append(test_resolvability.test_resolver(
  #     depsolver_integrate.resolve_via_depsolver, # resolver function
  #     DEPS_SIMPLE5_SOLUTION, #expected result
  #     'x(1)', # dist to install
  #     DEPS_SIMPLE5, # dependency data
  #     use_raw_deps=True # Do not convert deps to edeps - func expects deps.
  # ))

  # successes.append(test_resolvability.test_resolver(
  #     depsolver_integrate.resolve_via_depsolver, # resolver function
  #     DEPS_SIMPLE6_SOLUTION, #expected result
  #     'x(1)', # dist to install
  #     DEPS_SIMPLE6, # dependency data
  #     use_raw_deps=True # Do not convert deps to edeps - func expects deps.
  # ))

  # This one tests an unresolvable conflict.
  successes.append(test_resolvability.test_resolver(
      depsolver_integrate.resolve_via_depsolver, # resolver function
      testdata.DEPS_UNRESOLVABLE_SOLUTION, #expected result
      'x(1)', # dist to install
      testdata.DEPS_UNRESOLVABLE, # dependency data
      use_raw_deps=True, # Do not convert deps to edeps - func expects deps.
      expected_exception=depresolve.UnresolvableConflictError
  ))



  # Now try a conversion of all deps into depsolver format.
  # We need to load the full dependencies dict
  depdata.ensure_data_loaded()

  assert(len(depdata.dependencies_by_dist))

  (deps_serious_depsolver, dists_unable_to_convert) = \
      depsolver_integrate.convert_packs_to_packageinfo_for_depsolver(
      depdata.dependencies_by_dist)

  assert len(depdata.dependencies_by_dist) == \
      len(deps_serious_depsolver) + len(dists_unable_to_convert), \
      'Programming error. Output of ' + \
      'convert_packs_to_packageinfo_for_depsolver does not make sense.'

  if not len(deps_serious_depsolver) > 100000:
      logger.info('Full conversion has failed. Number of converted packages '
          'is: ' + len(deps_serious_depsolver))
      successes.append(False)
  else:
    successes.append(True)
    


  assert False not in [success for success in successes], \
      "Some tests failed! Results are: " + str(successes)


  logger.info("All tests in main() successful. (: (:")






#   TEST DEPSOLVER_INTEGRATE
def test_depsolver_version_str_conversion():
  testset = [
      ('1', '1.0.0'),
      ('2.3', '2.3.0'),
      ('41.3.0', '41.3.0'),
  ]

  for (ver_in, ver_expected) in testset:
    ver_out = depsolver_integrate.convert_version_into_depsolver(ver_in)
    if ver_out != ver_expected:
      raise Exception('Test failed. For ver_in of "' + ver_in + '", expected '
          '"' + ver_expected + '", but got instead: "' + ver_out + '".')

  logger.info("Version string conversion test successful. (:")
  return True





def test_depsolver_conversion():
  """
  Tests convert_deps_to_packageinfo_for_depsolver
  """
  expected_depsolver_deps = DEPS_SIMPLE_PACKAGEINFOS
  (depsolver_deps, dists_unable_to_convert) = \
      depsolver_integrate.convert_packs_to_packageinfo_for_depsolver(
      testdata.DEPS_SIMPLE)

  logger.info(depsolver_deps)

  assert set(expected_depsolver_deps) == set(depsolver_deps), \
      'Conversion failed:\n  Expected: ' + str(expected_depsolver_deps) + \
      '\n  Got:      ' + str(depsolver_deps)
  
  assert len(dists_unable_to_convert) == 0

  logger.info("test_depsolver_conversion(): Test passed.")

  return True # Test success




def test_depsolver_conversion2():
  """
  Tests convert_deps_to_packageinfo_for_depsolver, but uses more complex
  version strings.
  """
  (depsolver_deps, dists_unable_to_convert) = \
      depsolver_integrate.convert_packs_to_packageinfo_for_depsolver(
      DEPS_EDGE_CASES)
  logger.info('Product of DEPS_EDGE_CASES conversion:\n' + str(depsolver_deps))
  
  assert len(dists_unable_to_convert) == 0
  logger.info("test_depsolver_conversion2(): Test passed.")

  return True # Test success





def test_depsolver_conversion3():
  """
  Tests convert_deps_to_packageinfo_for_depsolver, but uses more complex
  version strings.
  """
  (depsolver_deps, dists_unable_to_convert) = \
      depsolver_integrate.convert_packs_to_packageinfo_for_depsolver(
      testdata.DEPS_MODERATE)

  logger.info('Product of DEPS_MODERATE conversion:\n' + str(depsolver_deps))

  assert len(dists_unable_to_convert) == 0
  logger.info("test_depsolver_conversion3(): Test passed.")

  return True # Test success





# DEPS_SIMPLE_DEPSOLVER_SOLUTION = \
#     'Installing a (3.0.0)\n' + \
#     'Installing c (1.0.0)\n' + \
#     'Installing b (1.0.0)\n' + \
#     'Installing x (1.0.0)\n'

DEPS_SIMPLE_PACKAGEINFOS = [
    depsolver_integrate.depsolver.PackageInfo.from_string('x-1.0.0; depends (b, c)'),
    depsolver_integrate.depsolver.PackageInfo.from_string('b-1.0.0; depends (a >= 2.0.0, a < 4.0.0)'),
    depsolver_integrate.depsolver.PackageInfo.from_string('c-1.0.0; depends (a == 3.0.0)'),
    depsolver_integrate.depsolver.PackageInfo.from_string('a-1.0.0'),
    depsolver_integrate.depsolver.PackageInfo.from_string('a-2.0.0'),
    depsolver_integrate.depsolver.PackageInfo.from_string('a-3.0.0'),
    depsolver_integrate.depsolver.PackageInfo.from_string('a-4.0.0')]

DEPS_EDGE_CASES = {
    'pip-accel(0.9.10)': [
        ['a', ''],
        ['b', '>0.1']
    ],
    'a(2)': [],
    'a(1)': [],
    'b(1)': [  ['a', '>=2,<4']  ],
}
# DEPS_EDGE_CASES_DEPSOLVER_SOLUTION = \
#     'Installing pip_accel (0.9.10)\n' + \
#     'Installing A (2.0.0)\n' + \
#     'Installing B (1.0.0)\n'

DEPS_EDGE_CASES_SOLUTION = sorted(['pip-accel(0.9.10)', 'b(1)', 'a(2)'])


if __name__ == '__main__':
  main()

