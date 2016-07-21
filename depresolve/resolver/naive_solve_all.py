import depresolve
import depresolve.depdata as data
import depresolve.resolver.resolvability as ry
import json
import depresolve._external.timeout as timeout

FNAME_SOLUTIONS = 'data/piplike_sols.json'
FNAME_ERRORS = 'data/piplike_errs.json'

def naive_solve_all(distkeys, edeps, vbp):
  naive_sols = data.load_json_db(FNAME_SOLUTIONS)
  naive_errs = data.load_json_db(FNAME_ERRORS)

  try:

    for k in distkeys:
      if k not in naive_sols and k not in naive_errs:
        try:
          print('Trying to solve for ' + k)
          naive_sols[k] = ry.naive_satisfy_timeout(k, edeps, vbp)
          print('Succeeded in solving for ' + k)
        except depresolve.MissingDependencyInfoError as e:
          naive_errs[k] = str(e)
          print('Missing dependency info for ' + k)
        except depresolve.NoSatisfyingVersionError as e:
          naive_errs[k] = str(e)
        except RecursionError:
          naive_errs[k] = 'RecursionError: maximum recursion depth exceeded ' + \
              'in comparison'
          print('Recursion depth exceeded for ' + k)
        except timeout.TimeoutException:
          naive_errs[k] = 'TimeoutError'
          print('Timed out while solving for ' + k)


  except:
    print('Process interrupted. Dumping files to abort locations.')
    json.dump(naive_sols, open(FNAME_SOLUTIONS+'.aborted', 'w'))
    json.dump(naive_errs, open(FNAME_ERRORS+'.aborted', 'w'))

  else:
    print('Finished. Dumping files.')
    json.dump(naive_sols, open(FNAME_SOLUTIONS, 'w'))
    json.dump(naive_errs, open(FNAME_ERRORS, 'w'))
