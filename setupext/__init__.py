# -*- coding: UTF-8 -*-


# Standard:
from __future__ import absolute_import, division, unicode_literals
import ast
import imp


def extract_details(name):
    docstring = version = None
    module = imp.find_module(name)[0]

    # Avoid having to import the module.
    with module:
        for node in ast.walk(ast.parse(module.read())):
            if isinstance(node, ast.Module):
                docstring = ast.get_docstring(node)
            elif isinstance(node, ast.Assign):
                if any(target.id == '__version__' for target in node.targets):
                    version = ast.literal_eval(node.value)

            if None not in (docstring, version):
                return (name, docstring, version)

    raise Exception('unable to extract module information: ' + name)


def to_install_requires(requirements):
    return [
        name if version is None else name + version
        for name, version in requirements.items()]


def to_requires(requirements):
    return [
        name if version is None else '%s(%s)' % (name, version)
        for name, version in requirements.items()]
