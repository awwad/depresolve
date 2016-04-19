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

DEPS_SIMPLE = {
    'X(1)': [  ['B', ''], ['C', '']  ],
    'B(1)': [  ['A', '>=2,<4']  ],
    'C(1)': [  ['A', '==3']  ],
    'A(1)': [],
    'A(2)': [],
    'A(3)': [],
    'A(4)': [],
}
DEPS_SIMPLE_SOLUTION = sorted(['X(1)', 'B(1)', 'C(1)', 'A(3)'])


# If B is handled before C, we must backtrack to solve this
# dependency conflict, as B2 will be chosen.
DEPS_SIMPLE2 = {
    'X(1)': [  ['B', []], ['C', []]],
    'B(2)': [],
    'B(1)': [],
    'C(1)': [  ['B', '<=1']  ],
}
DEPS_SIMPLE2_SOLUTION = sorted(['X(1)', 'B(1)', 'C(1)'])


DEPS_SIMPLE3 = {
    'X(1)': [  ['B', ''], ['C', '']  ],
    'B(2)': [],
    'B(1)': [],
    'C(1)': [  ['D', '' ]  ],
    'D(1)': [  ['B', '==1']  ]
}
DEPS_SIMPLE3_SOLUTION = sorted(['X(1)', 'B(1)', 'C(1)', 'D(1)'])

DEPS_SIMPLE4 = {
    'X(1)': [  ['B', []], ['C', []]],
    'B(1)': [  ['E', []]  ],
    'C(1)': [  ['D', []]  ],
    'D(1)': [  ['E', '==1']  ],
    'E(1)': [],
    'E(2)': []
}
DEPS_SIMPLE4_SOLUTION = sorted(['X(1)', 'B(1)', 'C(1)', 'D(1)', 'E(1)'])


# Same as DEPS_SIMPLE2, but with slightly diverse version strings.
# (for depsolver_integrate testing)
DEPS_SIMPLE5 = {
    'X(1)': [  ['B', ''], ['C', '']  ],
    'B(2.0)': [],
    'B(1.0.0)': [],
    'C(1)': [  ['B', '<=1.0.1']  ],
}
DEPS_SIMPLE5_SOLUTION = sorted(['X(1)', 'B(1.0.0)', 'C(1)'])

# Same as DEPS_SIMPLE2, but with very diverse version strings.
DEPS_SIMPLE6 = {
    'X(1.0)': [  ['B', ''], ['C', '']  ],
    'B(2.0b)': [],
    'B(1.0.0alpha)': [],
    'C(1-neg)': [  ['B', '<=1.0.1beta']  ],
}
DEPS_SIMPLE6_SOLUTION = sorted(['X(1.0)', 'B(1.0.0alpha)', 'C(1-neg)'])


# This is an unresolvable conflict.
DEPS_UNRESOLVABLE = {
    'X(1)': [  ['B', '>=2'], ['C', '']  ],
    'B(2)': [],
    'B(1)': [],
    'C(1)': [  ['B', '<=1']  ],
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
    'X(1)': [  ['B', []], ['C', []]],
    'B(1)': [  ['A', '>=2,<4']  ],
    'C(1)': [  ['A', '==3']  ],
    'A(1)': [],
    'A(2)': [],
    'A(3)': [],
    'A(4)': [],
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

