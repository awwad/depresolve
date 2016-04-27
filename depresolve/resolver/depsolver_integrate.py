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

import json

logger = depresolve.logging.getLogger('depsolver_integrate')

# Exception indicating that a dist cannot be converted to a depsolver
# PackageInfo object due to incompatibility - e.g. its own version string or
# a version string of a dependency it has cannot be converted for depsolver's
# use.
class DepsolverConversionError(ValueError):
  pass


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
  
  # While depsolver has a depsolver.errors.InvalidVersion it throws here,
  # it cannot actually be depended on to filter all errors. It fails to realize
  # that its own code chokes on '1.99', for example, and so we get various
  # diverse errors....
  except Exception as e: #depsolver.errors.InvalidVersion:
    # depsolver cannot understand the version string.
    # Try normalizing here.
    # First, find out if pip can handle it. If not, give up.
    try:
      pipified_ver = str(pip._vendor.packaging.version.parse(ver_str))

    except pip._vendor.packaging.version.InvalidVersion:
      raise DepsolverConversionError('Neither pip nor depsolver can parse this'
          ' version str:"' + ver_str + '". Giving up on converting for '
          'depsolver.')

    else:
      # Pip was able to make sense of the version string, but depsolver wasn't.
      # We'll try converting.

      # Conversion 1: Just try what pip understood it as. (Low probability.)
      try:
        semver = depsolver.version.SemanticVersion.from_string(pipified_ver)

      # Conversion 2: Check to see if it's partially specified. (High prob.)
      except Exception: #depsolver.errors.InvalidVersion:
        n_periods_in_verstring = ver_str.count('.')

        if 0 == n_periods_in_verstring:
          new_ver_str += '.0.0'

        elif 1 == n_periods_in_verstring:
          new_ver_str += '.0'

        else:
          raise DepsolverConversionError('Unable to convert version str "' +
              ver_str + '". pip understood it as "' + pipified_ver + '", but '
              'enthought/depsolver did not understand that, either, and it is '
              'not clear how to convert it.')

        # We added '.0' or '.0.0'. Try again now.
        try:
          semver = depsolver.version.SemanticVersion.from_string(new_ver_str)

        except Exception: #depsolver.errors.InvalidVersion:
          raise DepsolverConversionError('Unable to convert the version '
              'string. Received "' + ver_str + '". depsolver raised error on '
              'it. pip understood it as "' + pipified_ver + '". Tried that and'
              ' "' + new_ver_str + '". depsolver raised errors on all three.')

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
  try:
    my_ds_distkey = convert_packname_for_depsolver(packname)

    if as_req:
      my_ds_distkey += '=='
    else:
      my_ds_distkey += '-'

    my_ds_distkey += convert_version_into_depsolver(version)

  except Exception as e:
    raise DepsolverConversionError('Unable to convert distkey for depsolver.'
        ' Original error is: ' + str(e.args))

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





def convert_packname_for_depsolver(packname):
  """
  e.g. pip-accel to pip_accel
  depsolver has constraining package name requirements. /:

  TODO: Look into depsolver._package_utils.is_valid_package_name()
  and depsolver._package_utils.parse_package_full_name()
  """
  return packname.replace('-', '_')





def convert_packname_from_depsolver(depsolver_packname):
  """
  Revert from depsolver's package name format to that expected by pip and my
  code. (Reverses convert_packname_for_depsolver, the package name part of
  convert_distkey_for_depsolver.)

  TODO: Look into depsolver._package_utils.parse_package_full_name()
  """
  return depsolver_packname.replace('_', '-')





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
  try:
    my_ds_distkey = convert_distkey_for_depsolver(distkey)

  except DepsolverConversionError as e:
    logger.exception('In converting dist ' + distkey + ', unable to convert '
      'the distkey itself into a depsolver compatible name.')
    raise


  # Convert the dependencies.....
  my_ds_deps = ''

  for dep in deps[distkey]:
    # dep is e.g. ['A', '>=2,<4']
    satisfying_packname = convert_packname_for_depsolver(dep[0])
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
    logger.debug('convert_dist_to_packageinfo_for_depsolver produced: ' +
        ds_packageinfostr)

  try:
    pinfo = depsolver.PackageInfo.from_string(ds_packageinfostr)

  except Exception as e:
    raise DepsolverConversionError('\nUnable to convert ' + distkey + ' for '
        'depsolver. Original exception follows:\n' + str(e.args))

  return pinfo





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

  Returns two values:
    - the converted dependencies
    - a list of distkeys of dists we were unable to convert
  """

  packageinfos = []
  packs_unable_to_convert = []

  for distkey in deps:
    try:
      packageinfos.append(
          convert_dist_to_packageinfo_for_depsolver(distkey, deps))

    except DepsolverConversionError as e:
      logger.exception('In converting dictionary of dependencies into a '
          'depsolver-compatible format, unable to convert information for '
          'dist ' + distkey + '. Skipping and continuing with other dists. '
          'This may lead to inability to resolve package dependencies if '
          'this dist was part of a solution.')
      packs_unable_to_convert.append(distkey)
      # We continue here (no raise).

  return packageinfos, packs_unable_to_convert





def reload_already_converted_from_json(fname):
  """
  Given a json containing an array of the repr() values from
  depsolver.package.PackageInfo objects, re-instantiates those objects.
  (That is how I am storing the converted objects offline, as the conversion
  is time-consuming, and this re-instantiation is faster.)

  Discards any that do not parse correctly.
  AFAIK, that currently happens during this reload only if the dependencies
  for a given package were malformed to begin with in a certain specific way,
  at which point they can't be reloaded here due to a bug in
  depsolver.package.PackageInfo.repr(). Since these could not have been used
  anyway due to malformed dependency strings (originally from the bad packages'
  setup.py files), this is not any real loss.

  (
  Details:
  Example malformed dependency string: '==1.0,==1.1,==1.2'. This would not
  work in pip or otherwise and is simply a bad dist. They show up in
  PackageInfos here with version 'None'. While depsolver seems to be able to
  deal with these (by ignoring them), it sadly cannot reload them, as repr()
  spits them out in such a way that they cannot actually be used to
  re-instantiate the object.
  )
  """

  converted = json.load(open(fname, 'r'))
  pinfos = []
  #unable_to_parse = []
  n_unable_to_parse = 0
  i = 0

  for pinfo_str in converted:
    i += 1

    try:
      pinfos.append(depsolver.package.PackageInfo.from_string(str(pinfo_str))) # cleansing unicode bullshit with str() call

    except Exception as e:
      print('\n')
      print('Unable to parse, so skipping failed PackageInfo creation (' + 
          str(i) + ' of ' + str(len(converted)) + ': ' + pinfo_str)
      #print('Exception reads: ' + str(e.args))
      #unable_to_parse.append() # TODO: get distkeys here
      n_unable_to_parse += 1
      # continuing

  print('Unable to parse ' + str(n_unable_to_parse) + ' out of ' + str(i) +
      ' dists.')

  return pinfos





def resolve_via_depsolver(distkey, deps, versions_by_package=None,
    already_converted=False):
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

  If optional arg 'already_converted' is set to True, we take deps as depsolver
  compatible deps (PackageInfos), skipping any conversion process.

  """
  # Convert the dependencies into a format for depsolver, if they are not
  # already in a depsolver-friendly format.
  converted_dists = []
  dists_unable_to_convert = []

  if already_converted:
    converted_dists = deps
  else:
    (converted_dists, dists_unable_to_convert) = \
        convert_packs_to_packageinfo_for_depsolver(deps)

  
  # Create a depsolver "Repository" object containing a PackageInfo object for
  # each dist we know about from the deps dictionary of distributions.
  # NOTE: Inserting weird hack for now. These packages may already have a repo
  # for whatever reason. THIS HACK IS BAD AND MUST BE TEMPORARY.
  repo = None
  if converted_dists[0]._repository is not None:
    repo = converted_dists[0]._repository
  else:
    repo = depsolver.Repository(converted_dists)

      
  # Create an empty "Repository" to indicate nothing installed yet.
  installed_repo = depsolver.Repository()

  # A depsolver Pool is an abstraction encompassing the state of a repository
  # and what is installed locally. /:
  pool = depsolver.Pool([repo, installed_repo])

  # Putative installations are requests.
  request = depsolver.Request(pool)

  # This produces a sort of diff object that can be applied to the repository.
  # Installation would not actually occur. It's a request to install.
  try:
    request.install(
        depsolver.Requirement.from_string(convert_distkey_for_depsolver(
        distkey, as_req=True)))

  except DepsolverConversionError as e:
    logger.exception('Unable to convert given distkey to install into a '
        'depsolver-compatible format. Given distkey: ' + distkey)
    raise


  try:
    depsolver_solution = [operation for operation in 
        depsolver.Solver(pool, installed_repo).solve(request)]

  except NotImplementedError as e: # Sadly, this is what depsolver throws.
    logger.debug("Caught NotImplementedError from depsolver: \n" +
        str(e.args) + "\n")
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





def resolve_all_via_depsolver(dists_to_solve_for, pinfos, fname_solutions, fname_errors,
    fname_unresolvables):
  """
  Try finding the install solution for every dist in the list given, using
  dependency information from the given PackageInfo objects.

  Write this out to a temporary json occasionally so as not to lose data
  if the process is interrupted, as it is INCREDIBLY SLOW.

  """

  def _write_data_out(solutions, unable_to_resolve, unresolvables):
    """THIS IS AN INNER FUNCTION WITHIN resolve_all_via_depsolver!"""
    print('')
    print('------------------------')
    print('--- Progress So Far: ---')
    print('Solved: ' + str(len(solutions)))
    print('Error while resolving: ' + str(len(unable_to_resolve)))
    print('Unresolvable conflicts: ' + str(len(unresolvables)))
    print('Saving progress to json.')
    print('------------------------')
    print('')
    json.dump(solutions, open(fname_solutions, 'w'))
    json.dump(unable_to_resolve, open(fname_errors, 'w'))
    json.dump(unresolvables, open(fname_unresolvables, 'w'))


  solutions = dict()
  unable_to_resolve = []
  unresolvables = []
  i = 0

  for distkey in dists_to_solve_for:
    i += 1

    # TODO: Exclude the ones we don't have PackageInfo for (due to conversion
    # errors) so as not to skew the numbers. Currently, they should show up as
    # resolver errors.

    try:
      solution = \
          resolve_via_depsolver(distkey, pinfos, already_converted=True)

    # This is what the unresolvables look like:
    except depresolve.UnresolvableConflictError as e:

      unresolvables.append(str(distkey)) # cleansing unicode bullshit
      print(str(i) + '/' + str(len(dists_to_solve_for)) + ': Unresolvable: ' +
          distkey + '. (Error was: ' + str(e.args[0]))

    except Exception as e: # Many other potential causes of failure.

      unable_to_resolve.append(distkey)
      print(str(i) + '/' + str(len(dists_to_solve_for)) + ': Could not parse: '
          + distkey + '. Exception follows:' + str(e.args))

    else:
      solutions[distkey] = str(solution) # cleansing unicode bullshit
      print(str(i) + '/' + str(len(dists_to_solve_for)) + ': Resolved: ' +
          distkey)

    # Write early for my testing convenience.
    if i % 40 == 39:
      _write_data_out(solutions, unable_to_resolve, unresolvables)

  # Write at end.
  _write_data_out(solutions, unable_to_resolve, unresolvables)


