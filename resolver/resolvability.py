"""
<Program Name>
  Resolvability

<Purpose>
  Provides tools determining the resolvability of dependency conflicts.

  For definitions of resolvability, please see the pypi-depresolve project's
  readme, and what it links to.

"""

# Moved the code for dealing with dependency data directly into its own module,
# and should tweak this to use it as a separate module later.
import deptools

import resolver_sqli as sqli # the resolver's sqlite module

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






def fully_satisfy_strawman1(distkey, edeps, versions_by_package):
  """
  An exercise. Recurse and list all dists required to satisfy a dependency.
  Where there is ambiguity, select the first result from sort_versions().
  If multiple dists depend on the same package, we get both in this result.

  This has the same level of capability as pip's dependency resolution, though
  the results are slightly different.

  Arguments:
    - distkey ('django(1.8.3)'),
    - edeps (dictionary returned by deptools.deps_elaborated; see there.)
    - versions_by_package (dictionary of all distkeys, keyed by package name)

  Returns:
    - list of distkeys needed as direct or indirect dependencies to install the
      given distkey
  """
  my_edeps = edeps[distkey]
  if not my_edeps: # if no dependencies, return empty set
    return []

  satisfying_candidate_set = []

  for edep in my_edeps:
    satisfying_packname = edep[0]
    satisfying_versions = edep[1]
    if not satisfying_versions:
      raise NoSatisfyingVersion("Dependency of " + distkey + " on " + 
        satisfying_packname + " with specstring " + edep[2] + " cannot be "
        "satisfied: no versions found in elaboration attempt.")
    chosen_version = sort_versions(satisfying_versions)[0] # grab first
    chosen_distkey = deptools.get_distkey(satisfying_packname, chosen_version)
    satisfying_candidate_set.append(chosen_distkey)

    # Now recurse.
    satisfying_candidate_set.extend(
        strawman_fully_satisfy(chosen_distkey, edeps, versions_by_package))

  return satisfying_candidate_set


def satisfy_dependencies(distkey, dist_deps, versions_by_package, \
    using_tuples=False):
  """
  Takes the list of a single dist's dependencies and tries to find set of
  dists that satisfies all those dependencies.

  For now, I'll assume dist_deps is a list of 2-tuples like:
    (satisfying_package_name, specifier_string), e.g.:
    ('B', '>=5.0,<9')

  Example:
    this_dist == 'X(1)'
    dist_deps == [ ('B', ''), ('C', '') ]

  """
  if using_tuples:
    assert False, "Haven't written conversion here yet."
    #dist_deps = #some copied conversion of dist_deps

  print("Trying to solve for " + distkey + "'s dependencies:")
  print(dist_deps)

  satisfying_versions = dict()

  for dep in dist_deps:
    satisfying_packname = dep[0]
    specstring = dep[1]

    satisfying_versions[satisfying_packname] = \
        select_satisfying_versions(satisfying_packname, specstring, versions_by_package)









# ........
# Re-architecting from a different angle......
#

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


def sort_versions(versions):
  """
  Sort a list of versions such that they are ordered by most recent to least
  recent, with some prioritization based on which is best to install.

  STUB FUNCTION. To be written properly.
  Currently sorts reverse alphabetically, which is *clearly* wrong.
  """
  return sorted(versions, reverse=True)




if __name__ == "__main__":
  main()
