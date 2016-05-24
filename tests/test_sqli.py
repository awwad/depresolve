"""
<Program>
  test_sqli.py

<Purpose>
  Some unit tests for the sqlite3 interface for the dependency tools.

"""

import depresolve
import depresolve.depdata as depdata
import testdata
import depresolve.sql_i as sqli



def main():


  deps = testdata.DEPS_MODERATE
  versions_by_package = depdata.generate_dict_versions_by_package(deps)

  (edeps, packs_wout_avail_version_info, dists_w_missing_dependencies) = \
      depdata.elaborate_dependencies(deps, versions_by_package)

  assert depdata.are_deps_valid(testdata.DEPS_MODERATE) and \
      depdata.are_deps_valid(testdata.DEPS_SIMPLE), \
      'The test dependencies are coming up as invalid for some reason....'


  # Clear any pre-existing test database.
  sqli.initialize(db_fname='data/test_dependencies.db')
  sqli.delete_all_tables()

  sqli.populate_sql_with_full_dependency_info(
      edeps, versions_by_package, packs_wout_avail_version_info, 
      dists_w_missing_dependencies, db_fname='data/test_dependencies.db')


  print('All tests in main() OK.')




if __name__ == '__main__':
  main()
