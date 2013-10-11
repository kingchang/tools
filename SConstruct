# -*- coding: UTF-8 -*-


# Standard:
from __future__ import absolute_import, division, unicode_literals


env = Environment(tools = [
    'default', 'find', 'pep8', 'pylint', 'pyunit', 'travis-lint'])

src = env.Find('sources')

env.Default(env.Alias('check', [
    env.TravisLint(),
    env.Pep8(root = src, config = env.Find('pep8.ini')),
    env.Pylint(root = src, config = env.Find('pylint.ini')),
    env.PyUnit('test', root = src),
]))
