"""
<Program>
  testdata.py

<Purpose>
  Contains the basic test data for the various test modules.
  Some specialized data requiring external modules is in the individual test
  modules.

"""

import depresolve
import depresolve.deptools as deptools

import json # not really ideal here...

# Auxiliary test data (very large). Loaded by ensure_full_data_loaded().
DEPS_SERIOUS = None
EDEPS_SERIOUS = None
VERSIONS_BY_PACKAGE = None


def ensure_full_data_loaded():
  """
  Auxiliary test data (very large). Moving into an optional loading function
  so that it doesn't slow down anything that needs any test data.
  """
  global DEPS_SERIOUS
  global EDEPS_SERIOUS
  global VERSIONS_BY_PACKAGE

  if DEPS_SERIOUS is None:
    DEPS_SERIOUS = deptools.load_raw_deps_from_json('data/dependencies.json')

  if EDEPS_SERIOUS is None:
    EDEPS_SERIOUS = json.load(open('data/elaborated_dependencies.json', 'r'))

  if VERSIONS_BY_PACKAGE is None:
    VERSIONS_BY_PACKAGE = \
        deptools.generate_dict_versions_by_package(DEPS_SERIOUS)





DEPS_SIMPLE = {
    'x(1)': [  ['b', ''], ['c', '']  ],
    'b(1)': [  ['a', '>=2,<4']  ],
    'c(1)': [  ['a', '==3']  ],
    'a(1)': [],
    'a(2)': [],
    'a(3)': [],
    'a(4)': [],
}
DEPS_SIMPLE_SOLUTION = sorted(['x(1)', 'b(1)', 'c(1)', 'a(3)'])


# If B is handled before C, we must backtrack to solve this
# dependency conflict, as B2 will be chosen.
DEPS_SIMPLE2 = {
    'x(1)': [  ['b', ''], ['c', '']  ],
    'b(2)': [],
    'b(1)': [],
    'c(1)': [  ['b', '<=1']  ],
}
DEPS_SIMPLE2_SOLUTION = sorted(['x(1)', 'b(1)', 'c(1)'])


DEPS_SIMPLE3 = {
    'x(1)': [  ['b', ''], ['c', '']  ],
    'b(2)': [],
    'b(1)': [],
    'c(1)': [  ['d', '' ]  ],
    'd(1)': [  ['b', '==1']  ]
}
DEPS_SIMPLE3_SOLUTION = sorted(['x(1)', 'b(1)', 'c(1)', 'd(1)'])

DEPS_SIMPLE4 = {
    'x(1)': [  ['b', ''], ['c', '']  ],
    'b(1)': [  ['e', '']  ],
    'c(1)': [  ['d', '']  ],
    'd(1)': [  ['e', '==1']  ],
    'e(1)': [],
    'e(2)': []
}
DEPS_SIMPLE4_SOLUTION = sorted(['x(1)', 'b(1)', 'c(1)', 'd(1)', 'e(1)'])


# Same as DEPS_SIMPLE2, but with slightly diverse version strings.
# (for depsolver_integrate testing)
DEPS_SIMPLE5 = {
    'x(1)': [  ['b', ''], ['c', '']  ],
    'b(2.0)': [],
    'b(1.0.0)': [],
    'c(1)': [  ['b', '<=1.0.1']  ],
}
DEPS_SIMPLE5_SOLUTION = sorted(['x(1)', 'b(1.0.0)', 'c(1)'])

# Same as DEPS_SIMPLE2, but with very diverse version strings.
DEPS_SIMPLE6 = {
    'x(1.0)': [  ['b', ''], ['c', '']  ],
    'b(2.0b)': [],
    'b(1.0.0alpha)': [],
    'c(1-neg)': [  ['b', '<=1.0.1beta']  ],
}
DEPS_SIMPLE6_SOLUTION = sorted(['x(1.0)', 'b(1.0.0alpha)', 'c(1-neg)'])


# This is an unresolvable conflict.
DEPS_UNRESOLVABLE = {
    'x(1)': [  ['b', '>=2'], ['c', '']  ],
    'b(2)': [],
    'b(1)': [],
    'c(1)': [  ['b', '<=1']  ],
}
DEPS_UNRESOLVABLE_SOLUTION = None




DEPS_MODEL2 = {
    'motorengine(0.7.4)': [
        ['pymongo', '==2.5'],
        ['tornado', ''],
        ['motor', ''],
        ['six', ''],
        ['easydict', '']
    ],
    'pymongo(2.5)': [],
    'tornado(4.3)': [
        ['backports-abc', '>=0.4']
    ],
    'backports-abc(0.4)': [],
    'motor(0.5)': [
        ['greenlet', '>=0.4.0'],
        ['pymongo', '==2.8.0']
    ],
    'greenlet(0.4.9)': [],
    'pymongo(2.8)': [],
    'six(1.9.0)': [],
    'easydict(1.6)': []
}

DEPS_MODERATE = {
    'x(1)': [  ['b', ''], ['c', '']],
    'b(1)': [  ['a', '>=2,<4']  ],
    'c(1)': [  ['a', '==3']  ],
    'a(1)': [],
    'a(2)': [],
    'a(3)': [],
    'a(4)': [],
    'pip-accel(0.9.10)': [
        ['coloredlogs', '==0.4.3'],
        ['pip', '>=1.3']
    ],
    'autosubmit(3.0.4)': [
        ['six', ''],
        ['pyinotify', '']
    ],

    'coloredlogs(0.4.1)': [],
    'coloredlogs(0.4.3)': [],
    'coloredlogs(0.4.6)': [],
    'coloredlogs(0.4.7)': [],
    'coloredlogs(1.0.1)': [  ['humanfriendly', '>=1.25.1']  ],
    'coloredlogs(5.0)': [  ['humanfriendly', '>=1.42']  ],
    'six(1.1.0)': [],
    'six(1.2.0)': [],
    'six(1.3.0)': [],
    'six(1.4.0)': [],
    'six(1.4.1)': [],
    'six(1.5.1)': [],
    'six(1.5.2)': [],
    'six(1.6.0)': [],
    'six(1.6.1)': [],
    'six(1.7.0)': [],
    'six(1.7.2)': [],
    'six(1.7.3)': [],
    'six(1.8.0)': [],
    'six(1.9.0)': [],
    'six(1.10.0)': [],
    'pyinotify(0.9.0)': [],
    'pyinotify(0.9.1)': [],
    'pyinotify(0.9.2)': [],
    'pyinotify(0.9.3)': [],
    'pyinotify(0.9.4)': [],
    'pyinotify(0.9.5)': [],
    'pyinotify(0.9.6)': [],
    'humanfriendly(1.27)': [],
    'humanfriendly(1.42)': [],
    'humanfriendly(1.43.1)': [],
    'humanfriendly(1.5)': [],
}

CONFLICT_MODEL_3_SAMPLES = [
      'metasort(0.3.6)',
      'pillowtop(0.1.3)',
      'os-collect-config(0.1.8)',
      'openstack-doc-tools(0.7.1)',
      'python-magnetodbclient(1.0.1)']

UNRESOLVABLE_SAMPLES = [
      'gerritbot(0.2.0)',
      'exoline(0.2.3)',
      'openstack-doc-tools(0.21.1)']
