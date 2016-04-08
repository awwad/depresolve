"""
<Program Name>
  Resolvability

<Purpose>
  Provides tools determining the resolvability of dependency conflicts.

  For definitions of resolvability, please see the pypi-depresolve project's
  readme, and what it links to.

"""

import resolver # __init__ for errors and logging
import logging # grrr, actually use logging correctly, pls.
logging.basicConfig(level=logging.DEBUG)

# Moved the code for dealing with dependency data directly into its own module,
# and should tweak this to use it as a separate module later.
import resolver.deptools as deptools

import pip._vendor.packaging.specifiers

def main():
  convert_json_dep_to_elaborated_sql()


def convert_json_dep_to_elaborated_sql():
  deps = deptools.load_raw_deps_from_json()

  # First, I need a dict of available package versions given package name P.
  versions_by_package = deptools.generate_dict_versions_by_package(deps)

  # Elaborate deps into lists of specific satisfactory versions.
  # We'll parse the version constraints in the dependency into a
  # SpecifierSet, from pip._vendor.packaging.specifiers.SpecifierSet along
  # the way.
  (
      deps_elaborated,
      packages_without_available_version_info,
      dists_with_missing_dependencies
  ) = deptools.elaborate_dependencies(deps, versions_by_package)

  # Feed this into the sqlite tables.
  deptools.populate_sql_with_full_dependency_info(
      deps_elaborated,
      versions_by_package,
      packages_without_available_version_info,
      dists_with_missing_dependencies)


  #json.dump(deps_elaborated, open(DEPENDENCIES_DB_ELABORATED_FILENAME, 'w'))
  #json.dump(missing_dependencies, open(DEPENDENCIES_DB_MISSING_FILENAME, 'w'))



def detect_model_2_conflict_from_distkey(distkey, edeps, versions_by_package):
  """
  Directly pull model 2 conflicts from the elaborated dependency data.
  (Note that there is a slight difference in definition, based on the way that
  sort_versions operates as compared to the way that pip selects versions.)

  Return True if there is a model 2 conflict in the dependencies of the given
  distkey, based on the elaborated dependencies and dist catalog given. Else, 
  False.

  """
  logger = resolver.logging.getLogger( \
      'resolvability.detect_model_2_conflict_from_distkey')

  candidates = fully_satisfy_strawman1(distkey, edeps, versions_by_package)

  logger.debug("Running with candidates: " + str(candidates))

  for candidate in candidates: # for each candidate distkey

    (packname, version) = deptools.get_pack_and_version(candidate)

    # Find other candidates with the same package name.
    competing_candidates = \
        [competitor for competitor in candidates if
        competitor.startswith(packname + '(') and competitor != candidate]

    if competing_candidates:
      logger.info("Found conflict between " + candidate + " and " + 
          str(competing_candidates))
      return True

  return False


def detect_direct_conflict(candidates):
  """
  Given a set of distkeys, determines whether those distkeys are in conflict
  with each other directly. In particular, returns True if there is a pair or
  more of distkeys in the set with the same package name but different package
  versions. Else, False.

  """
  logger = resolver.logging.getLogger('resolvability.detect_direct_conflict')

  logger.debug("Running with candidates: " + str(candidates))

  for candidate in candidates: # for each candidate distkey

    (packname, version) = deptools.get_pack_and_version(candidate)

    # Find other candidates with the same package name.
    competing_candidates = \
        [competitor for competitor in candidates if
        competitor.startswith(packname + '(') and competitor != candidate]

    if competing_candidates:
      logger.info("Found conflict between " + candidate + " and " + 
          str(competing_candidates))
      return True

  return False


def combine_candidate_sets(orig_candidates, addl_candidates):
  """
  Given a set of distkeys to install and a second set to add to the first set,
  returns the combined set, with no duplicates.

  """
  combined = list(set(orig_candidates + addl_candidates)) # unique

  # if detect_direct_conflict(combined):
  #   raise resolver.ConflictingVersionError("Found conflict in the sets: " +
  #     str(orig_candidates) + " and " + str(addl_candidates))

  # else:
  #   return combined

  return combined



def fully_satisfy_strawman1(depender_distkey, edeps, versions_by_package):
  """
  An exercise. Recurse and list all dists required to satisfy a dependency.
  Where there is ambiguity, select the first result from sort_versions().
  If multiple dists depend on the same package, we get both in this result.

  This has the same level of capability as pip's dependency resolution, though
  the results are slightly different.

  Arguments:
    - depender_distkey ('django(1.8.3)'),
    - edeps (dictionary returned by deptools.deps_elaborated; see there.)
    - versions_by_package (dictionary of all distkeys, keyed by package name)

  Returns:
    - list of distkeys needed as direct or indirect dependencies to install
      depender_distkey
  """

  logger = resolver.logging.getLogger('resolvability.fully_satisfy_strawman1')

  my_edeps = edeps[depender_distkey]
  if not my_edeps: # if no dependencies, return empty set
    return []

  satisfying_candidate_set = []

  for edep in my_edeps:
    satisfying_packname = edep[0]
    satisfying_versions = edep[1]
    if not satisfying_versions:
      raise resolver.NoSatisfyingVersionError("Dependency of " +
        depender_distkey + " on " + satisfying_packname + " with specstring " +
        edep[2] + " cannot be satisfied: no versions found in elaboration "
        "attempt.")
    chosen_version = sort_versions(satisfying_versions)[0] # grab first
    chosen_distkey = deptools.get_distkey(satisfying_packname, chosen_version)
    satisfying_candidate_set.append(chosen_distkey)

    # Now recurse.
    satisfying_candidate_set.extend(
        fully_satisfy_strawman1(chosen_distkey, edeps, versions_by_package))

  return satisfying_candidate_set



def fully_satisfy_strawman2(depender_distkey, edeps, versions_by_package,
    depth=0):
  """
  An exercise. Recurse and list all dists required to satisfy a dependency.
  
  This time, test for any potential conflicts when adding a dist to the
  satisfying_candidate_set, and only add to the satisfying_candidate_set when
  there isn't a conflict.

  This version loops forever on circular dependencies, and seems not to
  find some solutions where they exist. (Example of latter: metasort(0.3.6))
  UPDATE: Algorithm is wrong. See Daily Notes.

  Additionally, this recursion is extremely inefficient, and would profit from
  dynamic programming in general.

  Arguments:
    - depender_distkey ('django(1.8.3)'),
    - edeps (dictionary returned by deptools.deps_elaborated; see there.)
    - versions_by_package (dictionary of all distkeys, keyed by package name)

  Returns:
    - list of distkeys needed as direct or indirect dependencies to install
      depender_distkey, including depender_distkey
  """

  logger = resolver.logging.getLogger('resolvability.fully_satisfy_strawman2')
  resolver.logging.basicConfig(level=resolver.logging.DEBUG) # filename='resolver.log'


  my_edeps = edeps[depender_distkey] # my elaborated dependencies
  satisfying_candidate_set = [depender_distkey] # Start with ourselves.

  if not my_edeps: # if no dependencies, return only ourselves
    logger.info('    '*depth + depender_distkey + ' had no dependencies. '
        'Returning just it.')
    return satisfying_candidate_set


  for edep in my_edeps:

    satisfying_packname = edep[0]
    satisfying_versions = sort_versions(edep[1])
    chosen_version = None

    if not satisfying_versions:
      raise resolver.NoSatisfyingVersionError('Dependency of ' +
          depender_distkey + ' on ' + satisfying_packname + ' with specstring '
          + edep[2] + ' cannot be satisfied: no versions found in elaboration '
          'attempt.')

    logger.info('    '*depth + 'Dependency of ' + depender_distkey + ' on ' + 
        satisfying_packname + ' with specstring ' + edep[2] + ' is satisfiable'
        ' with these versions: ' + str(satisfying_versions))

    for candidate_version in sort_versions(satisfying_versions):
      logger.info('    '*depth + '  Trying version ' + candidate_version)

      candidate_distkey = deptools.get_distkey(satisfying_packname,
          candidate_version)

      # Would the addition of this candidate result in a conflict?
      # Recurse and test result.
      candidate_satisfying_candidate_set = \
          fully_satisfy_strawman2(candidate_distkey, edeps,
              versions_by_package, depth+1)
      combined_satisfying_candidate_set = combine_candidate_sets(
          satisfying_candidate_set, candidate_satisfying_candidate_set)

      if detect_direct_conflict(combined_satisfying_candidate_set):
        # If this candidate version conflicts, try the next.
        logger.info('    '*depth + '  ' + candidate_version + ' conflicted. '
            'Trying next.')
        continue
      else: # save the new candidates
        chosen_version = candidate_version
        satisfying_candidate_set = combined_satisfying_candidate_set
        logger.info('    '*depth + '  ' + candidate_version + ' fits. Next '
            'dependency.')
        break

    if chosen_version is None:
      raise resolver.UnresolvableConflictError('Dependency of ' + 
          depender_distkey + ' on ' + satisfying_packname + ' with specstring '
          + edep[2] + ' cannot be satisfied: versions found, but none had 0 '
          'conflicts.')

  return satisfying_candidate_set



def fully_satisfy_strawman3(distkey_to_satisfy, edeps, versions_by_package,
    _depth=0, _candidates=[]):
  """
  An exercise. Recurse and list all dists required to satisfy a dependency.
  
  strawman2-to-strawman3: This time, before recursing, check to see if the
  package already has a version in the candidate set. If so, check to see if
  that version satisfies the current candidate's dependency, and if so,
  use that version - if NOT, raise a package conflict error. Eliminate circular
  dependency loop issues.

  strawman1-to-strawman2: Test for any potential conflicts when adding a dist
  to the satisfying_candidate_set, and only add to the satisfying_candidate_set
  when there isn't a conflict.

  Additionally, this recursion is extremely inefficient, and would profit from
  dynamic programming in general.

  Arguments:
    - distkey_to_satisfy ('django(1.8.3)'),
    - edeps (dictionary returned by deptools.deps_elaborated; see there.)
    - versions_by_package (dictionary of all distkeys, keyed by package name)
    - _depth: recursion depth, optionally, for debugging output
    - _candidates: used in recursion: the list of candidates already
      chosen, both to avoid circular dependencies and also to select sane
      choices and force early conflicts (to catch all solutions)

  Returns:
    - list of distkeys needed as direct or indirect dependencies to install
      distkey_to_satisfy, including distkey_to_satisfy
  """

  logger = resolver.logging.getLogger('resolvability.fully_satisfy_strawman3')
  resolver.logging.basicConfig(level=resolver.logging.DEBUG) # filename='resolver.log'


  # (Not sure this check is necessary yet, but we'll see.)
  if detect_direct_conflict(_candidates + [distkey_to_satisfy,]):
    raise resolver.ConflictingVersionError("Can't install me! You already have"
      " a different version of me! I'm: " + distkey_to_satisfy + "; you had " +
      str(_candidates) + " as candidates to install already.")

  if distkey_to_satisfy in _candidates:
    # You've already got me, bud. Whatchu doin'? (Terminate recursion on
    # circular dependencies, since we're already covered.)
    return []

  # Start the set of candidates to install with what our parent (depender)
  # already needs to install, plus ourselves.
  satisfying_candidate_set = _candidates + [distkey_to_satisfy,]

  my_edeps = edeps[distkey_to_satisfy] # my elaborated dependencies

  if not my_edeps: # if no dependencies, return only what's already listed
    logger.info('    '*_depth + distkey_to_satisfy + ' had no dependencies. '
        'Returning just it.')
    return satisfying_candidate_set


  for edep in my_edeps:

    satisfying_packname = edep[0]
    satisfying_versions = sort_versions(edep[1])
    chosen_version = None

    if not satisfying_versions:
      raise resolver.NoSatisfyingVersionError('Dependency of ' +
          distkey_to_satisfy + ' on ' + satisfying_packname + ' with specstring '
          + edep[2] + ' cannot be satisfied: no versions found in elaboration '
          'attempt.')

    logger.info('    '*_depth + 'Dependency of ' + distkey_to_satisfy + ' on ' + 
        satisfying_packname + ' with specstring ' + edep[2] + ' is satisfiable'
        ' with these versions: ' + str(satisfying_versions))

    for candidate_version in sort_versions(satisfying_versions):
      logger.info('    '*_depth + '  Trying version ' + candidate_version)

      candidate_distkey = deptools.get_distkey(satisfying_packname,
          candidate_version)

      # Would the addition of this candidate result in a conflict?
      # Recurse and test result. Detect UnresolvableConflictError.
      # Because we're detecting such an error in the child, there's no reason
      # to still do detection of the combined set here in the parent, but I
      # will leave in an assert in case.
      try:
        candidate_satisfying_candidate_set = \
            fully_satisfy_strawman3(candidate_distkey, edeps,
            versions_by_package, _depth+1, satisfying_candidate_set)

      # I don't know that I should be catching both. Let's see what happens.
      except (resolver.ConflictingVersionError, resolver.UnresolvableConflictError):
        logger.info('    '*_depth + '  ' + candidate_version + ' conflicted. '
            'Trying next.')
        continue

      else: # Could design it so child adds to this set, but won't yet.
        combined_satisfying_candidate_set = combine_candidate_sets(
            satisfying_candidate_set, candidate_satisfying_candidate_set)

        assert not detect_direct_conflict(combined_satisfying_candidate_set), \
            "Programming error. See comments adjacent."

        # save the new candidates (could be designed away, but for now, keeping)
        chosen_version = candidate_version
        satisfying_candidate_set = combined_satisfying_candidate_set
        logger.info('    '*_depth + '  ' + candidate_version + ' fits. Next '
            'dependency.')
        break


    if chosen_version is None:
      raise resolver.UnresolvableConflictError('Dependency of ' + 
          distkey_to_satisfy + ' on ' + satisfying_packname +
          ' with specstring ' + edep[2] + ' cannot be satisfied: versions '
          'found, but none had 0 conflicts.')

  return satisfying_candidate_set






def sort_versions(versions):
  """
  Sort a list of versions such that they are ordered by most recent to least
  recent, with some prioritization based on which is best to install.

  STUB FUNCTION. To be written properly.
  Currently sorts reverse alphabetically, which is *clearly* wrong.
  """
  return sorted(versions, reverse=True)








# ........
# Re-architecting from a different angle......
# What if we try to work directly from the specifier strings, instead of
# elaborating dependencies.
#

# Alternative design scribbles
def still_resolvable_so_far(constraints, versions_by_package):
  """

  Fill in.

  Returns true if there is a set of dists to pick that satisfies the given
  single-level constraints on packages.

  The structure of the constraints argument:
    packagename-indexed dictionary with value being a list of 2-tuples,
      value 1 of such being a specifier string and value 2 of such being a
      means of identifying the source of the constraint (e.g. needed for B(1)
      which is needed for X(1)).
      e.g.:
        {'A': [
                ('>1', B(1)<--X(1)),
                ('<5', C(1)<--X(1))
              ],
         'B': [
                ('>1,<12, F(1)<--X(1))
              ],
         ...
        }

        In the case above, True is returned as long as there is at least one
        version of A available greater than 1 and less than 5 and a version of
        B greater than 1 and less than 12. If either is not true, False is
        returned.

  """
  for packname in constraints:
    sat_versions = \
        select_satisfying_versions(
            packname,
            [constraint[0] for constraint in constraints(package)],
            versions_by_package
        )

    if not sat_versions:
      return False


# def satisfy_dependencies(distkey, dist_deps, versions_by_package, \
#     using_tuples=False):
#   """
#   Takes the list of a single dist's dependencies and tries to find set of
#   dists that satisfies all those dependencies.

#   For now, I'll assume dist_deps is a list of 2-tuples like:
#     (satisfying_package_name, specifier_string), e.g.:
#     ('B', '>=5.0,<9')

#   Example:
#     this_dist == 'X(1)'
#     dist_deps == [ ('B', ''), ('C', '') ]

#   """
#   if using_tuples:
#     assert False, "Haven't written conversion here yet."
#     #dist_deps = #some copied conversion of dist_deps

#   print("Trying to solve for " + distkey + "'s dependencies:")
#   print(dist_deps)

#   satisfying_versions = dict()

#   for dep in dist_deps:
#     satisfying_packname = dep[0]
#     specstring = dep[1]

#     satisfying_versions[satisfying_packname] = \
#         select_satisfying_versions(satisfying_packname, specstring, versions_by_package)






def select_satisfying_versions(
    satisfying_packname,
    specstrings,
    versions_by_package):
  """
  Given the name of the depended-on package, a list of the specifier strings
  characterizing the version constraints of each dependency on that package,
  and a dictionary of all versions of all packages, returns the list of
  versions that would satisfy all given specifier strings (thereby satisfying
  all of the given dependencies).

  Returns an empty list if there is no intersection (no versions that would
  satisfy all given dependencies).

  Raises (does not catch) KeyError if satisfying_packname does not appear in
  versions_by_package (i.e. if there is no version info for it).
  """
  # Get all versions of the satisfying package. Copy the values.
  satisfying_versions = versions_by_package[satisfying_packname][:] 

  for specstring in specstrings:
    specset = pip._vendor.packaging.specifiers.SpecifierSet(specstring)
    # next line uses list because filter returns a generator
    satisfying_versions = list(specset.filter(satisfying_versions)) 

  return satisfying_versions






if __name__ == "__main__":
  main()
