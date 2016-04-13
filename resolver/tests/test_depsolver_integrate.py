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
import depsolver

import resolver.depsolver_integrate as depsolver_integrate # SAT solver

from resolver.tests.testdata import *



def main():
  test_depsolver_conversion()
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

