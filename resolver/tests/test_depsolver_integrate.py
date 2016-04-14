"""
<Program>
  test_resolvability.py

<Purpose>
  Some unit tests for resolver.resolvability and resolver.depsolver_integrate.
  (Can restructure to be more standard later.)

  Note that some extra data for the tests is at the end.

"""
import json

import resolver
import resolver.deptools as deptools
import resolver.resolvability as resolvability
import resolver.tests.test_resolvability as test_resolvability

import resolver.depsolver_integrate as depsolver_integrate # SAT solver

from resolver.tests.testdata import *



def main():
  test_depsolver_conversion()

  # Try out the SAT solver in depsolver by using the wrapper function in
  # depsolver_integrate and passing that to the resolver tester in
  # resolver.test_resolvability.
  successes = []
  successes.append(test_resolvability.test_resolver(
      depsolver_integrate.resolve_via_depsolver, # resolver function
      DEPS_SIMPLE_SOLUTION, #expected result
      'X(1)', # dist to install
      DEPS_SIMPLE, # dependency data
      use_raw_deps=True # Do not convert deps to edeps - func expects deps.
  ))


  # The next three test resolvable conflicts that my backtracker can't solve.
  successes.append(test_resolvability.test_resolver(
      depsolver_integrate.resolve_via_depsolver, # resolver function
      DEPS_SIMPLE2_SOLUTION, #expected result
      'X(1)', # dist to install
      DEPS_SIMPLE2, # dependency data
      use_raw_deps=True # Do not convert deps to edeps - func expects deps.
  ))

  successes.append(test_resolvability.test_resolver(
      depsolver_integrate.resolve_via_depsolver, # resolver function
      DEPS_SIMPLE3_SOLUTION, #expected result
      'X(1)', # dist to install
      DEPS_SIMPLE3, # dependency data
      use_raw_deps=True # Do not convert deps to edeps - func expects deps.
  ))

  successes.append(test_resolvability.test_resolver(
      depsolver_integrate.resolve_via_depsolver, # resolver function
      DEPS_SIMPLE4_SOLUTION, #expected result
      'X(1)', # dist to install
      DEPS_SIMPLE4, # dependency data
      use_raw_deps=True # Do not convert deps to edeps - func expects deps.
  ))


  # # The next two test complex versions strings and are otherwise the same as 2.
  # successes.append(test_resolvability.test_resolver(
  #     depsolver_integrate.resolve_via_depsolver, # resolver function
  #     DEPS_SIMPLE5_SOLUTION, #expected result
  #     'X(1)', # dist to install
  #     DEPS_SIMPLE5, # dependency data
  #     use_raw_deps=True # Do not convert deps to edeps - func expects deps.
  # ))

  # successes.append(test_resolvability.test_resolver(
  #     depsolver_integrate.resolve_via_depsolver, # resolver function
  #     DEPS_SIMPLE6_SOLUTION, #expected result
  #     'X(1)', # dist to install
  #     DEPS_SIMPLE6, # dependency data
  #     use_raw_deps=True # Do not convert deps to edeps - func expects deps.
  # ))

  # This one tests an unresolvable conflict.
  successes.append(test_resolvability.test_resolver(
      depsolver_integrate.resolve_via_depsolver, # resolver function
      DEPS_UNRESOLVABLE_SOLUTION, #expected result
      'X(1)', # dist to install
      DEPS_UNRESOLVABLE, # dependency data
      use_raw_deps=True, # Do not convert deps to edeps - func expects deps.
      expected_exception=resolver.UnresolvableConflictError
  ))



  assert [success for success in successes], "Some tests failed!"


  print("Tests successful. (:")



#   TEST DEPSOLVER_INTEGRATE
def test_depsolver_conversion():
  """
  Tests convert_deps_to_packageinfo_for_depsolver
  """
  expected_depsolver_deps = DEPS_SIMPLE_PACKAGEINFOS
  depsolver_deps = \
      depsolver_integrate.convert_packs_to_packageinfo_for_depsolver(
      DEPS_SIMPLE)

  print(depsolver_deps)

  assert set(expected_depsolver_deps) == set(depsolver_deps), \
      'Conversion failed:\n  Expected: ' + str(expected_depsolver_deps) + \
      '\n  Got:      ' + str(depsolver_deps)

  print("test_depsolver_conversion(): Test passed! :D")



DEPS_SIMPLE_DEPSOLVER_SOLUTION = \
    'Installing A (3.0.0)\n' + \
    'Installing C (1.0.0)\n' + \
    'Installing B (1.0.0)\n' + \
    'Installing X (1.0.0)\n'

DEPS_SIMPLE_PACKAGEINFOS = [
    depsolver_integrate.PackageInfo.from_string('X-1.0.0; depends (B, C)'),
    depsolver_integrate.PackageInfo.from_string('B-1.0.0; depends (A >= 2.0.0, A < 4.0.0)'),
    depsolver_integrate.PackageInfo.from_string('C-1.0.0; depends (A == 3.0.0)'),
    depsolver_integrate.PackageInfo.from_string('A-1.0.0'),
    depsolver_integrate.PackageInfo.from_string('A-2.0.0'),
    depsolver_integrate.PackageInfo.from_string('A-3.0.0'),
    depsolver_integrate.PackageInfo.from_string('A-4.0.0')]

