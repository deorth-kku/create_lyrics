#!/bin/python3
import os
import pkgutil
import importlib

pkgpath = os.path.dirname(__file__)
pkgname = os.path.basename(pkgpath)

for _, file, _ in pkgutil.iter_modules([pkgpath]):
    # get a handle on the module
    mdl = importlib.import_module(pkgname+'.'+file)

    # is there an __all__?  if so respect it
    if "__all__" in mdl.__dict__:
        names = mdl.__dict__["__all__"]
    else:
        # otherwise we import all names that don't begin with _
        names = [x for x in mdl.__dict__ if not x.startswith("_")]

    # now drag them in
    globals().update({k: getattr(mdl, k) for k in names})
if __name__ == "__main__":
    pass
