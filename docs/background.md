# Dependency Resolution Background

##Resolvable Dependency Conflicts

Installation of a package may require a number of other packages, making these other packages dependencies of the first.

#### Example 1: Innocence
![Dependency Example 1](dep_conflict_examples.png "Dependency Example 1")

Your project nifty-webshop, a storefront webapp, might depend on django, for example. Version 1.1 of nifty-webshop might be written in python 3.4, and therefore need a version of django >= 1.7 (which is required for python 3.4+ support). You'd configure your package to list django>=1.7 as an install requirement, and so when a user runs `pip install nifty-webshop`, pip will grab the latest version of your nifty-webshop package, 1.1, figure out its dependencies (django>=1.7), fetch the latest version of django, and install both that and nifty-webshop. Tada.

#### Example 2
![Dependency Example 2](dep_conflict_examples2.png "Dependency Example 2")

Suppose you expand your successful project, releasing nifty-webshop 1.2, which can do some fun new things like delivery tracking by taking advantage of someone else's open source webapp, wheresmydelivery. nifty-webshop depends, then, on django>=1.7, and on wheresmydelivery (any version). Now, when a user tries to `pip install nifty-webshop`, pip will fetch nifty-webshop(1.2), see that it requires django>=1.7 and wheresmydelivery. pip will fetch both and see that the latest version of wheresmydelivery, wheresmydelivery(0.5) requires django>=1.5,<1.8. (Some of the django 1.8 changes break wheresmydelivery!)

You can see that now we have a potential **dependency conflict**! nifty-webshop needs django, and nifty-webshop needs wheresmydelivery, which also needs django... but the version ranges they need are not the same. In order to get a functioning set of installs (or at least an install set that satisfies all the various developers' stated requirements ^_^), we need to choose a version of django that satisfies both dependencies. In this case, it has to be django 1.7.x. Anything more or less fails to meet one of the requirements and breaks nifty-webshop directly or indirectly (by breaking wheresmydelivery). So, pip just has to install one of those, and all dependencies are met. That makes this dependency conflict **resolvable**: there is at least one solution that satisfies all stated dependencies.

The process of finding a set of package versions/dists that satisfies all requirements constitutes the problem of dependency resolution.


## Problem #1: ... Unfortunately, we don't even do THAT in python.

Unfotunately, when you `pip install nifty-webshop`, that simple resolution is not what actually happens, because [pip lacks a real dependency resolver](https://github.com/pypa/pip/issues/988). pip's approach is not a careful one, but rather a first-come-first-served approach that fails to recognize package conflicts like the one above. In the example above, it is likely that pip would grab nifty-webshop(1.2), django(1.9.x), and wheresmydelivery(0.5), install them all, and not even realize that it just broke the package it installed and provided the user a nonfunctioning install set. Thinking they've successfully installed, the user would at some point get arcane errors from wheresmydelivery because the version of django installed is not actually compatible with wheresmydelivery, and would break it. The performance of pip varies in this regard, and approximately 1.6% of dists currently on PyPI are packages with dependency conflicts that pip fails to resolve. (TODO: Link here to data when it's posted.) The number of hours users and developers lose debugging such *foreseeable problems* problems is not knowable.

Common approaches to 


##Problem #2: Unresolvable Dependency Conflicts

Further complicating matters, not all dependency conflicts even *are* resolvable.

<TODO: Expand on an example of an unresolvable conflict, say motorengine(0.7.4), explaining a few ways these happen. Even if a developer is mindful about the dependencies of her dependencies at dev time, new versions or different platforms can result in etc. etc. etc.>


![depresolve project components](docs/depresolve.png "depresolve project components")


