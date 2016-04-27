# Dependency Resolution Background

##Resolvable Dependency Conflicts

Installation of a package may require a number of other packages, making these other packages dependencies of the first.

#### Example 1: Innocence

Your project, nifty-webshop, a storefront webapp, depends on django. Version 1.1 of nifty-webshop is be written in python 3.4, and therefore needs a version of django >= 1.7 (which is required for python 3.4+ support). You'd configure your package to list django>=1.7 as an install requirement, and so when a user runs `pip install nifty-webshop`, pip will grab the latest version of your nifty-webshop package, 1.1, figure out its dependencies (django>=1.7), fetch the latest version of django, and install both that and nifty-webshop. Success!

![Dependency Example 1](dep_conflict_examples.png "Dependency Example 1")



#### Example 2

Suppose you expand your successful project, releasing nifty-webshop 1.2, which can do some fun new things like delivery tracking by taking advantage of someone else's open source webapp, wheresmydelivery. nifty-webshop depends, then, on django>=1.7, and on wheresmydelivery (any version). Now, when a user tries to `pip install nifty-webshop`, pip will fetch nifty-webshop(1.2) and see that it requires django>=1.7 and wheresmydelivery. pip will fetch both and see that the latest version of wheresmydelivery, wheresmydelivery(0.5), requires django>=1.5,<1.8. (Some of the django 1.8 changes break wheresmydelivery!)

![Dependency Example 2](dep_conflict_examples2.png "Dependency Example 2")

You can see that now we have a potential **dependency conflict**! nifty-webshop needs django, and nifty-webshop needs wheresmydelivery, which also needs django... but the version ranges they need are not the same. In order to get a functioning set of installs (or at least an install set that satisfies all the various developers' stated requirements ^_^), we need to choose a version of django that satisfies both dependencies. In this case, it has to be django 1.7.x. Anything more or less fails to meet one of the requirements and breaks nifty-webshop directly or indirectly (by breaking wheresmydelivery). So, pip just has to install one of those, and all dependencies are met. That makes this dependency conflict **resolvable**: there is at least one solution that satisfies all stated dependencies. (Some conflicts are unresolvable - a discussion of these is left for further down.)

The process of finding a set of package versions/dists that satisfies all requirements constitutes the problem of dependency resolution.



## Problem #1: ... Unfortunately, we don't even do THAT in python.

Unfortunately, when you `pip install nifty-webshop`, that simple resolution is not what actually happens, because [pip lacks a real dependency resolver](https://github.com/pypa/pip/issues/988). pip's approach is not a careful one, but rather a first-come-first-served approach that fails to recognize package conflicts like the one above. In the example above, it is likely that pip would grab nifty-webshop(1.2), django(1.9.x), and wheresmydelivery(0.5), install them all, and not even realize that it just broke the package it installed and provided the user a nonfunctioning install set. Thinking they've successfully installed, the user would at some point get arcane errors from wheresmydelivery because the version of django installed is not actually compatible with wheresmydelivery, and would break it. The performance of pip varies in this regard, and approximately 1.6% of dists currently on PyPI are packages with dependency conflicts that pip fails to resolve. (TODO: Link here to data when it's posted.) The number of hours users and developers lose debugging such *foreseeable problems* is not knowable. **It is noteworthy that this struggle would be improved by simply consistently notifying users (and, conditional on environment assumptions, even package uploaders and maintainers) of the existence of a conflict in the selected solution.**

As for automatic resolution of the dependency conflict problem, common approaches to finding a packaging dependency solution are **backtracking resolution** and **satisfiability (SAT) solving**.


## SAT Solving vs Blind Backtracking

The dependency conflict problem plagues package managers in general, and SAT solving, as the highly optimized and well studied discipline, is automatically the privileged candidate; however, PyPI is slightly special. PyPI package dependencies are not known until install time, i.e. are not fixed metadata; a package can actually dynamically decide what its dependencies are at install time, based on a user's environment (or any other arbitrary reason).

Consequently, for us, there is a substantial problem with a general SAT solver (which may employ backtracking internally in its search of the solution space or not - don't let that confuse you): that a SAT solver requires complete information about the dependency tree to begin. While in most practical cases, dependencies are static, dependency information does not *necessarily* exist independently of user environments. In particular, this means that unless we are willing to dictate or assume static package dependencies (and store them in some central dictionary - about 30MB - that every user would need and which is likely to occasionally diverge from the real dependencies they see), then **in order to SAT solve dependencies with a general SAT solver, a user would have to determine package dependency information for every applicable version of every dependend-on package, acquiring all the possible packages and processing their setup.py files.** That is massive overhead.

 By comparison, a backtracking resolver can simply pull package information as it is needed, and hope that the solution appears readily. What it loses in efficiency is likely to pale in comparison to the gains in not having to obtain and process a large number of distributions (django 1.7.1, 1.7.2, 1.7.3, 1.7......).

 It may be that a hybrid solution may prove worthwhile, with a centrally calculated solution set generated on some common environment and partially recalculated when new packages surface. The solution for a requested package X given to users when they try to install package X, and, if that fails for the user, backtracking can take over.







##Miscellanea

###Problem #2: Unresolvable Dependency Conflicts

Further complicating matters, not all dependency conflicts *are* resolvable.

--TODO: Expand on an example of an unresolvable conflict, say motorengine(0.7.4), explaining a few ways these happen. Even if a developer is mindful about the dependencies of her dependencies at dev time, new versions or different platforms can result in etc. etc. etc.--


