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

  NOTE THAT THIS module requires external packages depsolver and six!
  depsolver can be obtained here: https://github.com/enthought/depsolver


"""

import depresolve
import depresolve.deptools as deptools
import depresolve.resolver.resolvability as ry

import depsolver # external

import pip._vendor.packaging.specifiers # for SpecifierSet



#########################################################
########### Basic Conversion Functions ##################
#########################################################

def convert_version_from_depsolver(semantic_version):
  """
  Convert version format depsolver is using (depsolver.SemanticVersion) into
  version format I'm using (string of loose form '1.56.3a').

  Currently, for proof of concept and initial tests, we're using versions that
  fit the SemanticVersion spec instead of PyPI's sometimes elaborate ones.
  Depsolver can't accept anything other than exactly 3 numeric units (3.5.0,
  15.3.4, etc.).

  For the time being, I'm not converting them back in any way, since it's not
  really clear how to. I may need to update conflict checking, blacklisting,
  or anything else that might consume these version strings coming from
  depsolver to take into account the possible version string ambiguity.

  For now, this is just being used to provide solutions for human consumption,
  so the ambiguous version strings are OK. It does muck with unit tests, but
  I'll live with that for now (or rewrite part of test_resolvability to
  compare the versions selected intelligently instead of just as strings, so
  that things like '3' being the same as '3.0.0' will be caught.)

  """
  return str(semantic_version)



def convert_version_into_depsolver(ver_str):
  """
  Convert version format I'm using for now to one for depsolver, which is very
  restrictive about version numbers.

  This is an unpleasant mapping. ^_^
  """

  new_ver_str = ver_str
  pipified_ver = None # paranoid declaration in case of nested try scope issue
  semver = None # paranoid declaration in case of nested try scope issue

  # 1: try parsing into a 
  try:
    semver = depsolver.version.SemanticVersion.from_string(ver_str)
  
  except depsolver.errors.InvalidVersion:
    # depsolver cannot understand the version string.
    # Try normalizing here.
    # First, find out if pip can handle it. If not, give up.
    try:
      pipified_ver = str(pip._vendor.packaging.version.Version(ver_str))

    except pip._vendor.packaging.version.InvalidVersion:
      raise ValueError('Neither pip nor depsolver can parse this version str:'
          '"' + ver_str + '". Giving up on converting for depsolver.')

    else:
      # Pip was able to make sense of the version string, but depsolver wasn't.
      # We'll try converting.

      # Conversion 1: Just try what pip understood it as. (Low probability.)
      try:
        semver = depsolver.version.SemanticVersion.from_string(pipified_ver)

      # Conversion 2: Check to see if it's partially specified. (High prob.)
      except depsolver.errors.InvalidVersion:
        n_periods_in_verstring = ver_str.count('.')

        if 0 == n_periods_in_verstring:
          new_ver_str += '.0.0'

        elif 1 == n_periods_in_verstring:
          new_ver_str += '.0'

        else:
          raise ValueError('Unable to convert version str "' + ver_str
              + '". pip understood it as "' + pipified_ver + '", but '
              'enthought/depsolver did not understand that, either, and it is '
              'not clear how to convert it.')

        # We added '.0' or '.0.0'. Try again now.
        try:
          semver = depsolver.version.SemanticVersion.from_string(new_ver_str)

        except depsolver.errors.InvalidVersion:
          raise ValueError('Unable to convert the version string. Received "' +
              ver_str + '". depsolver raised error on it. pip understood '
              'it as "' + pipified_ver + '". Tried that and "' +
              new_ver_str + '". depsolver raised errors on all three.')

  assert semver is not None, "Programming error."
  
  return str(semver)






def convert_distkey_for_depsolver(distkey, as_req=False):
  """
  Convert the distkey to one usable by depsolver.
  e.g. 'X(1)' to 'X-1.0.0'
  e.g. 'pip-accel(1.0.0) to 'pip_accel-1.0.0'.
  (Shudder)
  """
  (packname, version) = deptools.get_pack_and_version(distkey)
  
  # depsolver can't handle '-' in package names (ARGH!), so turn all '-' to '_'
  # Must turn them back in the conversion back........
  my_ds_distkey = packname.replace('-', '_')

  if as_req:
    my_ds_distkey += '=='
  else:
    my_ds_distkey += '-'

  my_ds_distkey += convert_version_into_depsolver(version)

  return my_ds_distkey


# def convert_distkey_from_depsolver(depsolver_distkey):
#   """
#   Revert from depsolver's package name format to that expected by pip and my
#   code. (Reverses convert_distkey_for_depsolver.)
#   """

#   # Note that there are no dashes in depsolver pack names.
#   index_of_first_dash = depsolver_distkey.find('-')

#   packname = depsolver_distkey[: index_of_first_dash]
#   version = depsolver_distkey[index_of_first_dash+1 :]

#   # Convert back from depsolver's backward name constraints.
#   packname = packname.replace('_', '-')
  
#   return deptools.distkey_format(packname, version)

def convert_packname_from_depsolver(depsolver_packname):
  """
  Revert from depsolver's package name format to that expected by pip and my
  code. (Reverses the package name part of convert_distkey_for_depsolver.)
  """
  return depsolver_packname.replace('-', '_')



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
    specstring = dep[1]
    this_ds_dep = ''


    # Split up the specifier string into a dependency format depsolver will
    # understand.
    # Deps here look like ['django', '>=1.8.3,<=1.9']
    # That must come to look like:
    #   '... depends (django >= 1.8.3, django <= 1.9.0)'

    # if version is not constrained, e.g. [ 'A', '' ]
    if not specstring:
      this_ds_dep = satisfying_packname + ', '


    else: # version is constrained, e.g. ['A', '>=1.8.3,<=1.9']

      ops_and_versions = split_specstring_into_ops_and_versions(specstring)

      # import ipdb
      # ipdb.set_trace()

      for op_and_version in ops_and_versions:
        op = op_and_version[0]
        ver = op_and_version[1]
        this_ds_dep += satisfying_packname + ' ' + op + ' ' + \
            convert_version_into_depsolver(ver) + ', '

    my_ds_deps += this_ds_dep

  ds_packageinfostr = my_ds_distkey
  if my_ds_deps:
    # remove excess terminal ', ' from spooled deps.
    assert len(my_ds_deps) > 2, "Programming error."
    my_ds_deps = my_ds_deps[:-2]

    ds_packageinfostr += '; depends (' + my_ds_deps + ')'
    print('convert_dist_to_packageinfo_for_depsolver produced: ' +
        ds_packageinfostr)

  #import ipdb
  #ipdb.set_trace()
  return depsolver.PackageInfo.from_string(ds_packageinfostr)





def split_specstring_into_ops_and_versions(spec):
  """
  Convert a single specifier's string (e.g. '>=1.8.3', as a piece of
  '>=1.8.3,<1.9') into operator and version strings
  (in this case, '>=' and '1.8.3')
  Does this using pip's Specifier class.
  """
  specset = pip._vendor.packaging.specifiers.SpecifierSet(spec)
  ops_and_versions = []

  for spec in specset._specs:
    ops_and_versions.append([spec.operator, spec.version])
  
  return ops_and_versions





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

  Raises depresolve.UnresolvableConflictError if depsolver seems to detect
  an unresolvable conflict (which it does by raising, of all things, a
  NotImplementedError ): )

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

  try:
    depsolver_solution = [operation for operation in 
        depsolver.Solver(pool, installed_repo).solve(request)]

  except NotImplementedError, e: # Sadly, this is what depsolver throws.
    print("Caught NotImplementedError from depsolver: \n" + str(e.args) + "\n")
    raise depresolve.UnresolvableConflictError('Unable to resolve conflict '
        'via depsolver SAT solver. Presume that the distribution ' + distkey +
        ' has an unresolvable conflict.')

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
    packname = convert_packname_from_depsolver(install.package.name)
    version = convert_version_from_depsolver(install.package.version)
    distkey = deptools.distkey_format(packname, version)

    parsed_depsolver_solution.append(distkey)

  return parsed_depsolver_solution, None, None

