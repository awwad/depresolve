"""
<Program Name>
  Resolvability

<Purpose>
  Provides tools determining the resolvability of dependency conflicts, and
  attempts to provide a backtracking resolver for such conflicts.

  For definitions of resolvability, please see the pypi-depresolve project's
  readme, and what it links to.

"""

import depresolve # __init__ for errors and logging

# Moved the code for dealing with dependency data directly into its own module,
# and should tweak this to use it as a separate module later.
import depresolve.depdata as depdata
import depresolve._external.timeout as timeout # to kill too-slow resolution
import pip._vendor.packaging # for pip's specifiers and versions





def detect_model_2_conflict_from_distkey(distkey, edeps, versions_by_package):
  """
  Directly pull model 2 conflicts from the elaborated dependency data.
  (Note that there may be a slight difference in definition, based on the way
  that sort_versions operates as compared to the way that pip selects
  versions.)

  Return True if there is a model 2 conflict in the dependencies of the given
  distkey, based on the elaborated dependencies and dist catalog given. Else, 
  False. (See conflict definitions in README.md / background.md)

  """
  logger = depresolve.logging.getLogger(
      'resolvability.detect_model_2_conflict_from_distkey')

  candidates = fully_satisfy_strawman1(distkey, edeps, versions_by_package)

  logger.debug("Running with candidates: " + str(candidates))

  for candidate in candidates: # for each candidate distkey

    (packname, version) = depdata.get_pack_and_version(candidate)

    # Find other candidates with the same package name.
    competing_candidates = \
        [competitor for competitor in candidates if
        competitor.startswith(packname + '(') and competitor != candidate]

    if competing_candidates:
      logger.info("Found conflict between " + candidate + " and " + 
          str(competing_candidates))
      return True

  return False





def dist_lists_are_equal(distlist1, distlist2):
  """
  Returns True if the two given lists of dists are equal - that is, if they
  contain all the same versions of the same packages. No dist may exist in only
  one list and not the other.

  This function may fail if there are multiple versions of the same package in
  a single list.

  Version equality is not simply string matching, but equality of pip's
  Version objects. (This treats v 2 as the same as v 2.0.0, for example.)

  Runtime: O(N^2)
  """

  logger = depresolve.logging.getLogger('resolvability.dist_lists_are_equal')

  if len(distlist1) != len(distlist2):
    logger.debug('dist lists do not have the same length, thus are not equal.')
    return False


  # Convert to [  (nameA, verA), (nameB, verB), (nameC, verC)  ] format for
  # code convenience below.
  dists1 = []
  dists2 = []
  for distkey in distlist1:
    (pack, ver) = depdata.get_pack_and_version(distkey)
    dists1.append( (pack, ver) )
  for distkey in distlist2:
    (pack, ver) = depdata.get_pack_and_version(distkey)
    dists2.append( (pack, ver) )


  # Do the check for list1 vs list2 as well as list2 vs list1.
  for (thislist, otherlist) in [ (dists1, dists2), (dists2, dists1) ]:

    for (pack, ver) in thislist:
      # Easy case positive, where it exists with same version string:
      if (pack, ver) in otherlist:
        # We don't need to worry about multiples, as that is covered by the
        # other checks combined with the matching lengths.
        continue

      # Items in otherlist that have same package name as current item in
      # thislist.
      possible_matches = [v for (p, v) in otherlist if p == pack]

      # Easy case negative, where there's no dist of the same pack name in the
      # other set:
      if not possible_matches:

        logger.debug('This list contains "' + pack + '(' + ver + ')", but '
            'other list contains no dists of pack "' + pack + '". Lists not '
            'equal.')
        return False

      # Okay, we're in the harder case. There's at least one possible match,
      # but none of their versions are literal string matches. We have to make
      # sure that (at least) one of them has the same effective version.
      
      match_found = False

      for match_ver in possible_matches:
        if depdata.versions_are_equal(ver, match_ver):
          match_found = True
          break

      if not match_found:
        # If we haven't continued by the end of that for loop, then there is no
        # matching version of (pack,ver) from thislist in otherlist, so the
        # lists are not equal.
        return False

      # else continue to the next dist to check a match for in thislist.

  return True # Unable to find mismatch





def find_dists_matching_packname(packname, distkey_list):
  """
  Given a package name packname (e.g. django) and a list of distkeys (e.g.
  ['django(1.8.3)', 'foo(1)', 'mysql-python(1.1.1)']), returns the distkeys
  in that set that match the package name given. In the case given, returns
  'django(1.8.3)'.

  Returns [] if none match (that is, if the list of distributions does not
  include a distribution of the given package).

  Runtime: O(N)
  """
  matched_dists = []

  for distkey in distkey_list:
    if packname == depdata.get_packname(distkey):
      matched_dists.append(distkey)
  
  return matched_dists





def conflicts_with(distkey, distkey_set):
  """
  If there is an immediate conflict between a given dist and a given set of
  dists, returns the distkey of the dist from the set with which the given
  distkey conflicts. Else returns [] if no immediate conflict exists between
  the two.

  e.g. conflicts_with('django(1.5), ['django(1.3)', 'potato(2.5)']) returns
  ['django(1.3)'], indicating a conflict between django(1.5) and django(1.3).

  Runtime O(N)
  """
  (packname, version) = depdata.get_pack_and_version(distkey)

  # For more accurate version equality testing:
  pipified_version = pip._vendor.packaging.version.parse(version)

  # Find all matches for this distkey's package name in the given distkey_set
  # that are not the same literal distkey as this distkey.
  possible_competitors = \
      [dist for dist in find_dists_matching_packname(packname, distkey_set)
      if dist != distkey]


  # Check each possible conflict to be sure it's not actually the same version
  # (e.g. recognize version '2' as the same as version '2.0')
  competing_candidates = []
  for competitor_dist in possible_competitors:

    if not depdata.versions_are_equal(version,
        depdata.get_version(competitor_dist)):

      competing_candidates.append(competitor_dist)

  return competing_candidates





def detect_direct_conflict(candidates):
  """
  Given a set of distkeys, determines whether those distkeys are in conflict
  with each other directly. In particular, returns True if there is a pair or
  more of distkeys in the set with the same package name but different package
  versions. Else, False.

  Runtime: O(N^2)
  """
  logger = depresolve.logging.getLogger('resolvability.detect_direct_conflict')

  logger.debug("Running with candidates: " + str(candidates))

  for candidate in candidates: # for each candidate distkey

    competing_candidates = conflicts_with(candidate, candidates)

    if competing_candidates:
      logger.info("Found conflict between " + candidate + " and " + 
          str(competing_candidates))
      return True

  return False





def is_dep_satisfied(edep, candidates, disregard_setuptools=False):
  """
  Returns True if the given dependency (in the form of an elaborated
  dependency, or edep (See depresolve/depdata.py.)) is satisfied by the given
  list of candidate distkeys, else returns False.
  """
  logger = depresolve.logging.getLogger('resolvability.is_dep_satisfied')

  packname = edep[0]
  list_of_acceptable_versions = edep[1]

  if disregard_setuptools and packname in ['setuptools', 'pip', 'wheel']:
    return True

  same_package_dist = find_dists_matching_packname(packname, candidates)
  if not same_package_dist:
    logger.info('Not satisfied: No version of ' + packname + ' in candidate '
        'list.')
    return False
  assert len(same_package_dist) == 1, 'Programming error. Multiple dists of '\
      'the same package provided in a candidate list. N=' + \
      str(len(same_package_dist))
  same_package_dist = same_package_dist[0]

  version_of_satisfying_package = depdata.get_version(same_package_dist)
  
  # Slight shortcut to save time in the majority case:
  if version_of_satisfying_package in list_of_acceptable_versions:
    return True

  else:
    version_match = False
    # Doing it this way catches matches like 2.0 to 2.0.0. (Match same versions
    # even if string isn't exactly the same.)
    for acceptable_version in list_of_acceptable_versions:
      if depdata.versions_are_equal(version_of_satisfying_package,
          acceptable_version):
        version_match = True
        break

    return version_match

  assert False, 'Coding error. Should not be possible to reach this point.'





def are_fully_satisfied(candidates, edeps, versions_by_package,
    disregard_setuptools=False):
  """
  Validates the results of a resolver solution.
  Given a set of distkeys, determines whether or not all dependencies of all
  given dists are satisfied by the set (and all dependencies of their
  dependencies, etc.).
  Returns True if that is so, else returns False.

  Note that this depends on the provided dependency information in edeps.
  If those dependencies were harvested on a system that's different from the
  one that generated the given candidates (e.g. if even the python versions
  used are different), there's a chance the dependencies won't actually match
  since, as we know, PyPI dependencies are not static..............

  Arguments:
    1. candidates: a list of distkeys indicating which dists have been selected
           to satisfy each others' dependencies.
    2. edeps: elaborated dependencies (see depresolve/depdata.py)
    3. versions_by_package (as generated by
           depresolve.depdata.generate_dict_versions_by_package(); a dict of
           all versions for each package name))
    4. disregard_setuptools: optional. It breaks my heart to write this.
       Because for the rbtcollins resolver, I'm testing solutions generated by
       pip installs and harvested by pip freeze, I'm not going to get
       setuptools listed in the solution set (pip freeze doesn't list it), so
       ... for that, I pass in disregard_setuptools=True.

  Returns:
    - True or False

  Throws:
    - depresolve.MissingDependencyInfoError:
        if the dependencies data lacks info for one of the candidate dists.
        e.g. if solution employs a version not in the outdated dependency data

  """
  logger = depresolve.logging.getLogger('resolvability.are_fully_satisfied')

  # Lowercase the distkeys for our all-lowercase data, just in case.
  candidates = [distkey.lower() for distkey in candidates]

  for distkey in candidates:

    depdata.assume_dep_data_exists_for(distkey, edeps)

    for edep in edeps[distkey]:
      if not is_dep_satisfied(edep, candidates,
          disregard_setuptools=disregard_setuptools):
        logger.info(distkey + ' dependency ' + edep[0] + str(edep[2]) + ' is '
            'not satisfied by candidate set: ' + str(candidates) +
            '. Acceptable versions were: ' + str(edep[1]))
        return False

  return True





def combine_candidate_sets(orig_candidates, addl_candidates):
  """
  Given a set of distkeys to install and a second set to add to the first set,
  returns the combined set, with no duplicates.

  """
  combined = list(set(orig_candidates + addl_candidates)) # unique

  # if detect_direct_conflict(combined):
  #   raise depresolve.ConflictingVersionError("Found conflict in the sets: " +
  #     str(orig_candidates) + " and " + str(addl_candidates))

  # else:
  #   return combined

  return combined





def fully_satisfy_strawman1(depender_distkey, edeps, versions_by_package=None):
  """
  An exercise. Recurse and list all dists required to satisfy a dependency.
  Where there is ambiguity, select the first result from sort_versions().
  If multiple dists depend on the same package, we get both in this result.

  This has the same level of capability as pip's dependency resolution, though
  the results are slightly different.

  Arguments:
    - depender_distkey ('django(1.8.3)'),
    - edeps (dictionary returned by depdata.deps_elaborated; see there.)
    - versions_by_package (dictionary of all distkeys, keyed by package name)

  Returns:
    - list of distkeys needed as direct or indirect dependencies to install
      depender_distkey
  """

  logger = depresolve.logging.getLogger('resolvability.fully_satisfy_strawman1')

  if versions_by_package is None:
    versions_by_package = depdata.generate_dict_versions_by_package(edeps)

  depdata.assume_dep_data_exists_for(depender_distkey, edeps)

  my_edeps = edeps[depender_distkey]
  if not my_edeps: # if no dependencies, return empty set
    return []

  satisfying_candidate_set = []

  for edep in my_edeps:
    satisfying_packname = edep[0]
    satisfying_versions = edep[1]
    if not satisfying_versions:
      raise depresolve.NoSatisfyingVersionError("Dependency of " +
        depender_distkey + " on " + satisfying_packname + " with specstring " +
        edep[2] + " cannot be satisfied: no versions found in elaboration "
        "attempt.")
    chosen_version = sort_versions(satisfying_versions)[0] # grab first
    chosen_distkey = \
        depdata.distkey_format(satisfying_packname, chosen_version)
    satisfying_candidate_set.append(chosen_distkey)

    # Now recurse.
    satisfying_candidate_set.extend(
        fully_satisfy_strawman1(chosen_distkey, edeps, versions_by_package))

  return satisfying_candidate_set





def fully_satisfy_strawman2(depender_distkey, edeps, versions_by_package=None,
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
    - edeps (dictionary returned by depdata.deps_elaborated; see there.)
    - versions_by_package (dictionary of all distkeys, keyed by package name)

  Returns:
    - list of distkeys needed as direct or indirect dependencies to install
      depender_distkey, including depender_distkey
  """

  logger = depresolve.logging.getLogger('resolvability.fully_satisfy_strawman2')

  if versions_by_package is None:
    versions_by_package = depdata.generate_dict_versions_by_package(edeps)

  depdata.assume_dep_data_exists_for(depender_distkey, edeps)

  my_edeps = edeps[depender_distkey] # my elaborated dependencies
  satisfying_candidate_set = [depender_distkey] # Start with ourselves.

  if not my_edeps: # if no dependencies, return only ourselves
    logger.debug('    '*depth + depender_distkey + ' had no dependencies. '
        'Returning just it.')
    return satisfying_candidate_set


  for edep in my_edeps:

    satisfying_packname = edep[0]
    satisfying_versions = sort_versions(edep[1])
    chosen_version = None

    if not satisfying_versions:
      raise depresolve.NoSatisfyingVersionError('Dependency of ' +
          depender_distkey + ' on ' + satisfying_packname + ' with specstring '
          + edep[2] + ' cannot be satisfied: no versions found in elaboration '
          'attempt.')

    logger.debug('    '*depth + 'Dependency of ' + depender_distkey + ' on ' + 
        satisfying_packname + ' with specstring ' + edep[2] + ' is satisfiable'
        ' with these versions: ' + str(satisfying_versions))

    for candidate_version in sort_versions(satisfying_versions):
      logger.debug('    '*depth + '  Trying version ' + candidate_version)

      candidate_distkey = depdata.distkey_format(satisfying_packname,
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
        logger.debug('    '*depth + '  ' + candidate_version + ' conflicted. '
            'Trying next.')
        continue
      else: # save the new candidates
        chosen_version = candidate_version
        satisfying_candidate_set = combined_satisfying_candidate_set
        logger.debug('    '*depth + '  ' + candidate_version + ' fits. Next '
            'dependency.')
        break

    if chosen_version is None:
      raise depresolve.UnresolvableConflictError('Dependency of ' + 
          depender_distkey + ' on ' + satisfying_packname + ' with specstring '
          + edep[2] + ' cannot be satisfied: versions found, but none had 0 '
          'conflicts.')

  return satisfying_candidate_set





@timeout.timeout(300) # Timeout after 5 minutes.
def backtracking_satisfy(distkey_to_satisfy, edeps, versions_by_package=None):
  """
  Provide a list of distributions to install that will fully satisfy a given
  distribution's dependencies (and its dependencies' dependencies, and so on),
  without any conflicting or incompatible versions.

  This is a backtracking dependency resolution algorithm.
  
  This recursion is extremely inefficient, and would profit from dynamic
  programming in general.

  Note that there must be a level of indirection for the timeout decorator to
  work as it is currently written. (This function can't call itself directly
  recursively, but must instead call _backtracking_satisfy, which then can
  recurse.)


  Arguments:
    - distkey_to_satisfy ('django(1.8.3)'),
    - edeps (dictionary returned by depdata.deps_elaborated; see there.)
    - versions_by_package (dictionary of all distkeys, keyed by package name)
      (If not included, it will be generated from edeps.)

  Returns:
    - list of distkeys needed as direct or indirect dependencies to install
      distkey_to_satisfy, including distkey_to_satisfy

  Throws:
    - timeout.TimeoutException if the process takes longer than 5 minutes
    - depresolve.UnresolvableConflictError if not able to generate a solution
      that satisfies all dependencies of the given package (and their
      dependencies, etc.). This suggests that there is an unresolvable
      conflict.
    - depresolve.ConflictingVersionError
      (Should not raise, ideally, but might - requires more testing)
    - depresolve.NoSatisfyingVersionError
      (Should not raise, ideally, but might - requires more testing)

  """
  if versions_by_package is None:
    versions_by_package = depdata.generate_dict_versions_by_package(edeps)

  try:
    (satisfying_candidate_set, new_conflicts, child_dotgraph) = \
        _backtracking_satisfy(distkey_to_satisfy, edeps, versions_by_package)

  except depresolve.ConflictingVersionError as e:
    raise depresolve.UnresolvableConflictError('Unable to find solution to '
        'conflict with one of ' + distkey_to_satisfy + "'s immediate "
        'dependencies. Lower level conflict exception follows: ' + str(e))

  else:
    return satisfying_candidate_set





def _backtracking_satisfy(distkey_to_satisfy, edeps, versions_by_package,
    _depth=0, _candidates=[], _conflicting_distkeys=[]):
  """
  Recursive helper to backtracking_satisfy. See comments there.

  The ADDITIONAL arguments, for recursion state, are:
    - _depth: recursion depth, optionally, for debugging output
    - _candidates: used in recursion: the list of candidates already
      chosen, both to avoid circular dependencies and also to select sane
      choices and force early conflicts (to catch all solutions)
    - _conflicting_distkeys: similar to _candidates, but lists dists that
      we've established conflict with accepted members of _candidates. Saves
      time (minimal dynamic programming)

  The ADDITIONAL returns, for recursion state, are:
    - _conflicting_distkeys, for internal use in recursion
    - str, newline separated list, of the edges in the dot graph describing the
      dependencies satisifed here
      (e.g. 'X(1) -> B(1)\nX(1) -> C(1)\nC(1) -> A(3)\nB(1) -> A(3)')


  """
  logger = depresolve.logging.getLogger('resolvability.backtracking_satisfy')

  # (Not sure this check is necessary yet, but we'll see.)
  if conflicts_with(distkey_to_satisfy, _candidates):
    assert False, "This should be impossible now...."# Can't install me! You " +\
        #"already have a different version of me! I'm: " + distkey_to_satisfy +\
        #"; you had " + str(_candidates) + " as candidates to install already."
    #   str(_candidates) + " as candidates to install already.")
    #   " a different version of me! I'm: " + distkey_to_satisfy + "; you had " +
    #   str(_candidates) + " as candidates to install already.")
    # raise depresolve.ConflictingVersionError("Can't install me! You already have"
    #   " a different version of me! I'm: " + distkey_to_satisfy + "; you had " +
    #   str(_candidates) + " as candidates to install already.")

  # I think this should also be impossible now due to checks before this call
  # would be made?
  if distkey_to_satisfy in _candidates:
    assert False, "This should also be impossible now, I think."
    # You've already got me, bud. Whatchu doin'? (Terminate recursion on
    # circular dependencies, since we're already covered.)
    return [], [], ''

  # Start the set of candidates to install with what our parent (depender)
  # already needs to install, plus ourselves.
  satisfying_candidate_set = _candidates + [distkey_to_satisfy,]

  # Start a list of distkeys that conflict with us while we try to fulfil our
  # dependencies. (Prevents duplicating work)
  my_conflicting_distkeys = []

  # Identify the version of the package to install on the dotgraph. /:  
  dotgraph = dot_sanitize(depdata.get_packname(distkey_to_satisfy)) + \
      '[label = "' + distkey_to_satisfy + '"];\n'


  depdata.assume_dep_data_exists_for(distkey_to_satisfy, edeps)

  my_edeps = edeps[distkey_to_satisfy] # my elaborated dependencies

  if not my_edeps: # if no dependencies, return only what's already listed
    logger.debug('    '*_depth + distkey_to_satisfy + ' had no dependencies. '
        'Returning just it.')
    return satisfying_candidate_set, [], ''


  for edep in my_edeps:

    satisfying_packname = edep[0]
    satisfying_versions = sort_versions(edep[1])
    chosen_version = None

    if not satisfying_versions:
      raise depresolve.NoSatisfyingVersionError('Dependency of ' +
          distkey_to_satisfy + ' on ' + satisfying_packname + ' with '
          'specstring ' + edep[2] + ' cannot be satisfied: no versions found '
          'in elaboration attempt.')

    logger.debug('    '*_depth + 'Dependency of ' + distkey_to_satisfy + ' on ' 
        + satisfying_packname + ' with specstring ' + edep[2] + ' is '
        'satisfiable with these versions: ' + str(satisfying_versions))


    # Is there already a dist of this package in the candidate set?
    preexisting_dist_of_this_package = find_dists_matching_packname(
        satisfying_packname, satisfying_candidate_set)

    if preexisting_dist_of_this_package:
      assert 1 == len(preexisting_dist_of_this_package), \
          "Programming error." # Can't have more than 1 to begin with!
      # Set of 1 item -> 1 item.
      preexisting_dist_of_this_package = preexisting_dist_of_this_package[0]

      preexisting_version = \
          depdata.get_version(preexisting_dist_of_this_package)

      if preexisting_version in satisfying_versions:
        logger.debug('    '*_depth + 'Dependency of ' + distkey_to_satisfy +
            ' on ' + satisfying_packname + ' with specstring ' + edep[2] +
            ' is already satisfied by pre-existing candidate ' +
            preexisting_dist_of_this_package + '. Next dependency.')
        continue

      else:
        raise depresolve.ConflictingVersionError('Dependency of ' +
          distkey_to_satisfy + ' on ' + satisfying_packname + ' with '
          'specstring ' + edep[2] + ' conflicts with a pre-existing distkey in'
          ' the list of candidates to install: ' +
          preexisting_dist_of_this_package)


    for candidate_version in sort_versions(satisfying_versions):

      candidate_distkey = depdata.distkey_format(satisfying_packname,
          candidate_version)

      if candidate_distkey in _conflicting_distkeys:
        logger.debug('    '*_depth + '  Skipping version ' + candidate_version
            + '(' + candidate_distkey + '): already in _conflicting_distkeys.')
        continue
 
      # else try this version.
      logger.debug('    '*_depth + '  Trying version ' + candidate_version)


      # Would the addition of this candidate result in a conflict?
      # Recurse and test result. Detect UnresolvableConflictError.
      # Because we're detecting such an error in the child, there's no reason
      # to still do detection of the combined set here in the parent, but I
      # will leave in an assert in case.
      try:
        (candidate_satisfying_candidate_set, new_conflicts, child_dotgraph) = \
            _backtracking_satisfy(candidate_distkey, edeps,
            versions_by_package, _depth+1, satisfying_candidate_set)

      # I don't know that I should be catching both. Let's see what happens.
      except (depresolve.ConflictingVersionError,
          depresolve.UnresolvableConflictError):
        logger.debug('    '*_depth + '  ' + candidate_version + ' conflicted. '
            'Trying next.')
        my_conflicting_distkeys.append(candidate_distkey)
        continue

      else: # Could design it so child adds to this set, but won't yet.
        combined_satisfying_candidate_set = combine_candidate_sets(
            satisfying_candidate_set, candidate_satisfying_candidate_set)

        assert not detect_direct_conflict(combined_satisfying_candidate_set), \
            "Programming error. See comments adjacent."

        # save the new candidates (could be designed away, but for now, keeping)
        chosen_version = candidate_version
        satisfying_candidate_set = combined_satisfying_candidate_set
        my_conflicting_distkeys.extend(new_conflicts)

        # Save the graph visualization output for the new candidate.
        #dotgraph += dot_sanitize(satisfying_packname) + '[label = "' + \
        #    candidate_distkey + '"];\n'
        dotgraph += dot_sanitize(depdata.get_packname(distkey_to_satisfy)) + \
            ' -> ' + dot_sanitize(satisfying_packname) + ';\n' + child_dotgraph
        
        logger.debug('    '*_depth + '  ' + candidate_version + ' fits. Next '
            'dependency.')
        break


    if chosen_version is None:
      raise depresolve.UnresolvableConflictError('Dependency of ' + 
          distkey_to_satisfy + ' on ' + satisfying_packname +
          ' with specstring ' + edep[2] + ' cannot be satisfied: versions '
          'found, but none had 0 conflicts.')

  return satisfying_candidate_set, my_conflicting_distkeys, dotgraph





@timeout.timeout(300) # Timeout after 5 minutes.
def satisfy2(distkey_to_satisfy, edeps, versions_by_package):
  """
  Provide a list of distributions to install that will fully satisfy a given
  distribution's dependencies (and its dependencies' dependencies, and so on),
  without any conflicting or incompatible versions.

  This is a backtracking dependency resolution algorithm.
  
  Note that there must be a level of indirection for the timeout decorator to
  work as it is currently written. (This function can't call itself directly
  recursively, but must instead call _backtracking_satisfy, which then can
  recurse.)

  Note that this is not efficient.
  (Example: Queues are best implemented by collections.deque rather than list.)

  Arguments:
    - distkey_to_satisfy ('django(1.8.3)'),
    - edeps (dictionary returned by depdata.deps_elaborated; see there.)
    - versions_by_package (dictionary of all distkeys, keyed by package name)

  Returns:
    - list of distkeys needed as direct or indirect dependencies to install
      distkey_to_satisfy, including distkey_to_satisfy

  Throws:

  """
  logger = depresolve.logging.getLogger('resolvability.satisfy2')

  solution = [] # current solution 
  inclQ = [] # queue of dists to process for inclusion in solution set
  calcQ = [] # queue of version constraints to process

  # Algorithm
  #
  # Invariants:
  #   Include queue contains distributions that were selected to satisfy
  #   dependency constraints. They have their dependencies processed in turn,
  #   resulting in additions to the calc queue, and then they're added to the
  #   solution list (the current working solution).
  #
  #   Calc queue contains constraints like (conceptually) 'django < 1.8'. These
  #   are processed and items are added as a result to the include queue.
  #   If conflicts are observed in the processing of the calc queue, items can
  #   be removed from the solution and include queue, and additional
  #   constriants will be added to the calc queue. Once a constraint in the
  #   calc queue is processed, it is removed and we move on to the next one.
  #
  #   Once one of the queues is empty, we switch to the next queue, and we keep
  #   going until both are simultaneously empty, at which point we should have
  #   a nonconflicting solution.
  #

  # Add given distkey to the include queue.
  inclQ.append(distkey_to_satisfy)

  # Iterate until both queues are empty.
  while iQ or cQ:

    # Iterate until the include queue is empty.
    while iQ:
      assert False, 'Still writing this.'


    # Iterate until the calc queue is empty.
    while cQ: 
      assert False, 'Still writing this.'





#   solution = \
#       _satisfy2(distkey_to_satisfy, edeps, versions_by_package, incl, inclQ,
#       calcQ)



#   assert False, 'Still writing this.'


# def _satisfy2(distkey_to_satisfy, edeps, versions_by_package, _incl, _inclQ,
#     calcQ):
#   """
#   Helper for satisfy2's recursion. (Must be separate in order for the timeout
#   to work, plus probably easier to understand this way.)
#   """
#   logger = depresolve.logging.getLogger('resolvability.satisfy2')



#   assert False, 'Still writing this.'





def sort_versions(versions):
  """
  Sort a list of versions such that they are ordered by most recent to least
  recent, with some prioritization based on which is best to install.

  Instantiate all given objects as pip versions
  (pip._vendor.packaging.version.Version) and then sort those, then spit back
  the original strings associated with each in the sorted order.

  Note that technically some of the versions may instead be
  pip._vendor.packaging.version.LegacyVersion if they do not comply with
  PEP 440.

  This is used by backtracking_satisfy to prioritize version selection.
  """

  # Construct a list associating version string with pip version object.
  pipified_versions = []
  for v in versions:
    pipified_versions.append((pip._vendor.packaging.version.parse(v), v))

  # Sort that list in reverse order. (pip Versions have overriden comparisons,
  # sort keys, etc.)
  pipified_versions = sorted(pipified_versions, reverse=True)

  # Return just the version strings, but in the correct order now.
  return [v[1] for v in pipified_versions]






def resolve_all_via_backtracking(dists_to_solve_for, edeps,
    versions_by_package, fname_solutions, fname_errors, fname_unresolvables, ):
  """
  Try finding the install solution for every dist in the list given, using
  dependency information from the given elaborated dependencies dictionary.

  Write this out to a temporary json occasionally so as not to lose data
  if the process is interrupted, as it very slow.

  """

  logger = depresolve.logging.getLogger(
      'resolvability.resolve_all_via_backtracking')


  def _write_data_out(solutions, unable_to_resolve, unresolvables):
    """THIS IS AN INNER FUNCTION WITHIN resolve_all_via_depsolver!"""
    import json
    logger.info('------------------------')
    logger.info('--- Progress So Far: ---')
    logger.info('Solved: ' + str(len(solutions)))
    logger.info('Error while resolving: ' + str(len(unable_to_resolve)))
    logger.info('Unresolvable conflicts: ' + str(len(unresolvables)))
    logger.info('Saving progress to json.')
    logger.info('------------------------')
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

    logger.info(str(i) + '/' + str(len(dists_to_solve_for)) + ': Starting ' + 
        distkey + '....')

    try:
      solution = \
          backtracking_satisfy(distkey, edeps, versions_by_package)

    # This is what the unresolvables look like:
    except (depresolve.ConflictingVersionError,
        depresolve.UnresolvableConflictError) as e:

      unresolvables.append(str(distkey)) # cleansing unicode prefixes (python2)
      logger.info(str(i) + '/' + str(len(dists_to_solve_for)) + ': '
          'Unresolvable: ' + distkey + '. (Error was: ' + str(e.args[0]))

    # Other potential causes of failure, including TimeoutException
    except Exception as e:

      unable_to_resolve.append(str(distkey)) # cleansing unicode prefixes (py2)
      logger.info(str(i) + '/' + str(len(dists_to_solve_for)) + ': Could not '
          'parse: ' + distkey + '. Exception of type ' + str(type(e)) +
          ' follows:' + str(e.args))

    else:
      solutions[distkey] = [str(dist) for dist in solution] # cleansing unicode prefixes (python2)
      logger.info(str(i) + '/' + str(len(dists_to_solve_for)) +
          ': Resolved: ' + distkey)

    # Write early for my testing convenience.
    if i % 40 == 39:
      _write_data_out(solutions, unable_to_resolve, unresolvables)

  # Write at end.
  _write_data_out(solutions, unable_to_resolve, unresolvables)





# ........
# Re-architecting from a different angle......
# What if we try to work directly from the specifier strings, instead of
# elaborating dependencies.
#

# Alternative design scribbles
# def still_resolvable_so_far(constraints, versions_by_package):
#   """

#   Fill in.

#   Returns true if there is a set of dists to pick that satisfies the given
#   single-level constraints on packages.

#   The structure of the constraints argument:
#     packagename-indexed dictionary with value being a list of 2-tuples,
#       value 1 of such being a specifier string and value 2 of such being a
#       means of identifying the source of the constraint (e.g. needed for B(1)
#       which is needed for X(1)).
#       e.g.:
#         {'A': [
#                 ('>1', B(1)<--X(1)),
#                 ('<5', C(1)<--X(1))
#               ],
#          'B': [
#                 ('>1,<12, F(1)<--X(1))
#               ],
#          ...
#         }

#         In the case above, True is returned as long as there is at least one
#         version of A available greater than 1 and less than 5 and a version of
#         B greater than 1 and less than 12. If either is not true, False is
#         returned.

#   """
#   for packname in constraints:
#     sat_versions = \
#         select_satisfying_versions(
#             packname,
#             [constraint[0] for constraint in constraints(package)],
#             versions_by_package
#         )

#     if not sat_versions:
#       return False


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






# def select_satisfying_versions(
#     satisfying_packname,
#     specstrings,
#     versions_by_package):
#   """
#   Given the name of the depended-on package, a list of the specifier strings
#   characterizing the version constraints of each dependency on that package,
#   and a dictionary of all versions of all packages, returns the list of
#   versions that would satisfy all given specifier strings (thereby satisfying
#   all of the given dependencies).

#   Returns an empty list if there is no intersection (no versions that would
#   satisfy all given dependencies).

#   Raises (does not catch) KeyError if satisfying_packname does not appear in
#   versions_by_package (i.e. if there is no version info for it).
#   """
#   # Get all versions of the satisfying package. Copy the values.
#   satisfying_versions = versions_by_package[satisfying_packname][:] 

#   for specstring in specstrings:
#     specset = pip._vendor.packaging.specifiers.SpecifierSet(specstring)
#     # next line uses list because filter returns a generator
#     satisfying_versions = list(specset.filter(satisfying_versions)) 

#   return satisfying_versions



def dot_sanitize(packagename):
  """
  The .dot graphviz language has requirements for its labels that make it hard
  for me to automatically map dists one to one to labels for the dependency
  graphing I'd like to do.
  This hack just maps '-' and '.' to '_'. This mapping breaks 1-to-1, but
  I'll just have to live with it. Grumble grumble grumble.
  """
  return packagename.replace('-','_').replace('.','_')


