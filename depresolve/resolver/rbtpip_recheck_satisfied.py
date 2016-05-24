"""
Convenience script, one-time.
"""
import depresolve
import depresolve.depdata as depdata
import depresolve.resolver.resolvability as ry


def recheck_all_unsatisfied():
  depdata.ensure_data_loaded(CONFLICT_MODELS=[3], include_edeps=True)

  solutions = depdata.load_json_db('data/resolved_via_rbtpip.json')

  installed = [d for d in solutions if solutions[d][0]]
  satisfied = [d for d in solutions if solutions[d][1]]

  installed_but_unsatisfied = [d for d in installed if d not in satisfied]

  # We re-run this last set, to see if they're in fact unsatisfied.
  for distkey in installed_but_unsatisfied:
    satisfied, errstring = recheck_satisfied(distkey, solutions[distkey][2])

    if satisfied or errstring != solutions[distkey][3]:
      print('Updating satisfied-ness!: ' + distkey)
      solutions[distkey][1] = satisfied
      solutions[distkey][3] = errstring

    else:
      print('Still unsatisfied: ' + distkey + '. Error: ' + errstring)

  return solutions







def recheck_satisfied(distkey, solution):

  satisfied = False
  installed = distkey in [d.lower() for d in solution] # sanitize old data
  errstring = ''

  assert installed, 'Expecting solutions with distkey installed.'

  # Check to see if the solution is fully satisfied.
  # (Note that because virtual environments start off with pip,
  # wheel, and setuptools, we can't tell when a solution includes them,
  # don't store those as part of the solution, and so disregard them in this
  # dependency check. ):
  try:
    (satisfied, errstring) = ry.are_fully_satisfied(solution,
        depdata.elaborated_dependencies, depdata.versions_by_package,
        disregard_setuptools=True, report_issue=True)
  except depresolve.MissingDependencyInfoError as e:
    errstring = 'Unable to determine if satisfied: missing dep info for ' + \
        str(e.args[1])
    satisfied = ''   # evaluates False but is not False
    print(' ERROR! ' + errstring + '. Resolution for ' + distkey +
        ' unknown. Full exception:' + str(e))

  # Return the updated satisfied-ness of this distkey:
  #  - whether or not the install set is fully satisfied and conflict-less
  #  - error string if there was an error
  return (satisfied, errstring)
