"""
<Program Name>
  depsolver_integrate.py

<Purpose>
  Provides depsolver integration for my resolver and dependency tools.
  (Wraps depsolver to be compatible with my tools, e.g.
  test_deptools.test_resolver().)

  Essentially, this can be thought of as a SAT-solving extension for
  resolver.resolvability that wraps depsolver to be compatible. The end result
  is that these two will operate in the same compatible way:
      - resolver.depsolver_integration.resolver_via_depsolver()
      - resolver.resolvability.backtracking_solve()

  depsolver is a python-based dependency resolver employing SAT solving to
  handle dependency conflicts. It is an offshoot of "enthought".
  See https://github.com/enthought/depsolver

  Apologies for the unexpected namespace clash / difficult-to-distinguish
  names. Please don't mix this up with resolver or deptools. ):

"""

import resolver
import resolver.deptools as deptools
import resolver.resolvability as ry

from depsolver import * # external





#########################################################
########### Basic Conversion Functions ##################
#########################################################

def convert_version_from_depsolver(semantic_version):
  """
  Convert version format depsolver is using (depsolver.SemanticVersion) into
  version format I'm using (string of loose form '1.56.3a').
  """
  assert False, "Still writing."



def convert_version_into_depsolver(version_string):
  """
  Convert version format I'm using for now to one for depsolver, which is very
  restrictive about version numbers.

  This is an unpleasant mapping. ^_^
  For now, I assume my versions are all single-unit (e.g. '3', not '3.0')
  """
  return version_string + '.0.0' # cheesy assumption for now



def convert_distkey_for_depsolver(distkey, as_req=False):
  """
  Convert the distkey to one usable by depsolver.
  e.g. 'X(1)' to 'X-1.0.0'
  (Shudder)
  """
  (packname, version) = deptools.get_pack_and_version(distkey)
  my_ds_distkey = packname
  if as_req:
    my_ds_distkey += '=='
  else:
    my_ds_distkey += '-'

  my_ds_distkey += convert_version_into_depsolver(version)

  return my_ds_distkey




def convert_dist_to_packageinfo_for_depsolver(distkey, deps):
  """
  Given deps for a single distkey (e.g. DEPS_SIMPLE[X(1)] above), converts to
  a depsolver compatible format, depsolver.PackageInfo (e.g.
  DEPS_SIMPLE_PACKAGEINFOS[0] above)

  Returned object is type depsolver.PackageInfo.
  Further example of what is returned:
  depsolver.PackageInfo.from_string('B-1.0.0; depends (A >= 2.0.0, A < 4.0.0)')

  """

  # Convert the distkey to one usable by depsolver.
  my_ds_distkey = convert_distkey_for_depsolver(distkey)

  # Convert the dependencies.....
  my_ds_deps = ''

  for dep in deps[distkey]:
    # dep is e.g. ['A', [['>=', '2'], ['<', '4']]]
    satisfying_packname = dep[0]
    satisfying_specifiers = dep[1]
    this_ds_dep = ''

    # if version is not constrained, e.g. [ 'A', [] ]
    if not satisfying_specifiers:
      this_ds_dep = satisfying_packname + ', '

    else: # version is constrained, e.g. ['A', [ ['>', '2'], ['<=' '4'] ]]
      for spec in satisfying_specifiers:
        op = spec[0]
        ver = spec[1]
        this_ds_dep += satisfying_packname + ' ' + op + ' ' + \
            convert_version_into_depsolver(ver) + ', '

    my_ds_deps += this_ds_dep

  ds_packageinfostr = my_ds_distkey
  if my_ds_deps:
    # remove excess terminal ', ' from spooled deps.
    assert len(my_ds_deps) > 2, "Programming error."
    my_ds_deps = my_ds_deps[:-2]

    ds_packageinfostr += '; depends (' + my_ds_deps + ')'

  return depsolver.PackageInfo.from_string(ds_packageinfostr)






def convert_packs_to_packageinfo_for_depsolver(deps):
  """
  Given deps (e.g. DEPS_SIMPLE above), converts to a depsolver compatible
  format, depsolver.PackageInfo (e.g. DEPS_SIMPLE_PACKAGEINFOS above)

  Uses convert_single_dist_deps_to_packageinfo_for_depsolver
  """

  packageinfos = []

  for distkey in deps:
    packageinfos.append(
        convert_dist_to_packageinfo_for_depsolver(distkey, deps))

  return packageinfos






def resolve_via_depsolver(distkey, deps, versions_by_package=None):
  """
  Wrapper for the depsolver package so that it can be tested via the same
  testing I employ for my own resolver package.
  Solves a dependency structure for a given package's dependencies, using
  the external depsolver package.

  Intended to be compatible with resolver.deptools.test_resolver.
  e.g.:
  deptools.test_resolver(resolve_via_depsolver, DEPS_SIMPLE_DEPSOLVER_SOLUTION,
      'X(1)', DEPS_SIMPLE, use_raw_deps=True)

  Converts the output of depsolve back into a comprehensible format for
  resolver.resolvability. Mapping involves some ugly fudging of version
  strings.

  """
  # Create a depsolver "Repository" object containing a PackageInfo object for
  # each dist we know about from the deps dictionary of distributions.
  repo = depsolver.Repository(
      convert_packs_to_packageinfo_for_depsolver(deps))

  # Create an empty "Repository" to indicate nothing installed yet.
  installed_repo = depsolver.Repository()

  # A depsolver Pool is an abstraction encompassing the state of a repository
  # and what is installed locally. /:
  pool = depsolver.Pool([repo, installed_repo])

  # Putative installations are requests.
  request = depsolver.Request(pool)

  # This produces a sort of diff object that can be applied to the repository.
  # Installation would not actually occur. It's a request to install.
  request.install(
      depsolver.Requirement.from_string(convert_distkey_for_depsolver(distkey,
      as_req=True)))

  depsolver_solution = [operation for operation in 
      depsolver.Solver(pool, installed_repo).solve(request)]

  # What depsolver will have provided there will look like:
  #  [Installing A (3.0.0), Installing C (1.0.0), Installing B (1.0.0),
  #      Installing X (1.0.0)]
  #  where each of those is a depsolver.solver.operations.Install object....
  #
  # We want to strip the nonsense in it and return something like:
  #   ['X(1)', 'B(1)', 'C(1)', 'A(3)']
  # so that the output can be assessed by the resolver.test_deptools module.
  #
  parsed_depsolver_solution = []
  for install in depsolver_solution:
    packname = install.package.name
    version = convert_version_from_depsolver(install.package.version)
    distkey = deptools.get_distkey(packname, version)

    parsed_depsolver_solution.append(distkey)

  return parsed_depsolver_solution

