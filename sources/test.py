# -*- coding: UTF-8 -*-


# Standard:
from __future__ import absolute_import, division, unicode_literals
import unittest2

# Internal:
import argf


class TestParameters (unittest2.TestCase):
    def test_no_parameters(self):
        # pylint: disable=C0112

        def main():
            """"""
            return 123

        self.assertEqual(argf.start(main, args = []), 123)


class TestDocstring (unittest2.TestCase):
    def test_no_docstring(self):
        def main(length = 123):
            return length

        self.assertEqual(argf.start(main, args = []), 123)
