# -*- coding: UTF-8 -*-


# Standard:
from __future__ import absolute_import, division, unicode_literals
import os


# Not called, but required.
def exists(env):
    raise NotImplementedError()


def generate(env):
    """
    Adds a ``Which`` method to the SCons environment.
    """

    env.AddMethod(Which)


def Which(env, name, paths = None):
    """
    :param name: program name
    :type name: unicode
    :param paths: additional paths to search
    :type paths: list<unicode>
    :return: program path
    :rtype: unicode
    :raise Exception: program wasn't found
    """

    prog_path = env.Detect(name)

    if prog_path is not None:
        return prog_path

    if paths is None:
        paths = []

    for path_var in ('PATH',):
        path = os.environ.get(path_var)

        if path is not None:
            paths.extend(path.split(os.pathsep))

    prog_path = env.WhereIs(name, path = paths)

    if prog_path is not None:
        return prog_path

    raise Exception('Program not found: ' + name)
