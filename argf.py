# -*- coding: UTF-8 -*-


"""
Declarative command line arguments parser.

Builds options for an :py:class:`argparse.ArgumentParser` from a function's
parameters and docstring, and calls it with the program arguments already
parsed.

Help text is taken from the function's docstring:

* The main paragraph describes the program.
* Parameter descriptions describe program arguments.

Arguments are taken from the function's parameters:

* Non-keyword parameters are converted to positional arguments.
* Keyword parameters are converted to optional arguments.

  * Boolean parameters are converted to flag arguments.

Argument types are taken from the first available definition:

#. Parameter docstring type.
#. Keyword parameter's default value, unless ``None``.
#. Default to :py:data:`six.text_type`.
"""


# Standard:
from __future__ import absolute_import, division, unicode_literals
inspect = None # lazy
import re

# External:
argparse = None # lazy
docutils = None # lazy
six = None # lazy


__all__ = ['start']
__version__ = (0, 1, 0) # semver


# TODO: Use the `python_2_unicode_compatible` decorator for `__unicode__`?
class Error (Exception):
    pass


class AmbiguousDesc (Error):
    def __str__(self):
        return 'user defined arg parser instance already has a description'


class AmbiguousParamDesc (Error):
    def __str__(self):
        return 'ambiguous parameter description: %s' % self.args


class AmbiguousParamDataType (Error):
    def __str__(self):
        return 'ambiguous parameter data type: %s' % self.args


class DynamicArgs (Error):
    def __str__(self):
        return 'varargs and kwargs are not supported'


class IncompatibleParamDataTypes (Error):
    def __str__(self):
        return 'default value and docstring types are not compatible: %s' \
            % self.args


class UndefinedParamDataType (Error):
    def __str__(self):
        return 'undefined parameter data type: %s' % self.args


class UndefinedParamDesc (Error):
    def __str__(self):
        return 'undefined parameter description: %s' % self.args


class UnknownParams (Error):
    def __str__(self):
        (names,) = self.args
        return 'unknown parameter(s): ' + ', '.join(sorted(names))


class UnknownParamDataType (Error):
    def __str__(self):
        return 'unknown parameter data type: %s' % self.args


class TupleArg (Error):
    def __str__(self):
        (arg,) = self.args
        return 'tuple argument (parameter unpacking) is not supported: (%s)' \
            % ', '.join(arg)


class Argument (object):
    _WORD_SEPARATOR = '-'


    def __init__(self, name):
        super(Argument, self).__init__()

        self.name = name
        self.data_type = None
        self.description = None


    def add_to_parser(self, arg_parser):
        """
        :type arg_parser: argparse.ArgumentParser
        """

        options = {
            'metavar': self.get_actual_name(),
            'type': self.get_actual_data_type(),
        }

        if self.description is not None:
            options['help'] = self.description

        arg_parser.add_argument(self.name, **options)


    def get_actual_data_type(self):
        global six
        if six is None: # pragma: no cover
            import six

        if self.data_type is None:
            return six.text_type
        else:
            return self.data_type


    def get_actual_name(self):
        return self.name.strip('_').replace('_', self._WORD_SEPARATOR)


class OptionArgument (Argument):
    def __init__(self, name, default_value):
        super(OptionArgument, self).__init__(name)
        self.default_value = default_value


    def add_to_parser(self, arg_parser):
        """
        :type arg_parser: argparse.ArgumentParser
        """

        actual_name = self.get_actual_name()
        data_type = self.get_actual_data_type()
        names = [(2 * arg_parser.prefix_chars) + actual_name]

        options = {
            'default': self.default_value,
            'dest': self.name,
        }

        if self.description is not None:
            options['help'] = self.description

        # TODO: Add a "--no-[NAME]" counterpart option as well?
        if issubclass(data_type, bool):
            options['const'] = not self.default_value
            options['action'] = 'store_const'
        else:
            options['type'] = data_type

        reserved_chars = set([self._WORD_SEPARATOR])

        # TODO: Don't use undocumented functions.
        for option in arg_parser._option_string_actions.keys():
            if (len(option) == 2) and (option[0] == arg_parser.prefix_chars):
                reserved_chars.add(option[1])

        available_chars = actual_name.translate(
            dict((ord(ch), '') for ch in reserved_chars))

        if len(available_chars) > 0:
            names.append(arg_parser.prefix_chars + available_chars[0])

        arg_parser.add_argument(*names, **options)


    def get_actual_data_type(self):
        """
        :raise IncompatibleParamDataTypes:
        """

        if self.default_value is None:
            return super(OptionArgument, self).get_actual_data_type()
        elif self.data_type is None:
            return type(self.default_value)
        elif not isinstance(self.default_value, self.data_type):
            raise IncompatibleParamDataTypes(self.name)
        else:
            return self.data_type


def extract_arguments(function):
    """
    :type function: types.FunctionType
    :rtype: tuple<None | six.text_type, list<Argument>>
    :raise UnknownParams:
    """

    (main_desc, data_types, descriptions) = extract_documentation(function)
    args = []

    for param in extract_parameters(function):
        if isinstance(param, tuple):
            (name, default_value) = param
            arg = OptionArgument(name = name, default_value = default_value)
        else:
            arg = Argument(name = param)

        if arg.name in data_types:
            arg.data_type = data_types.pop(arg.name)

        if arg.name in descriptions:
            arg.description = descriptions.pop(arg.name)

        args.append(arg)

    if (len(data_types) > 0) or (len(descriptions) > 0):
        raise UnknownParams(set(data_types.keys()).union(descriptions.keys()))

    return (main_desc, args)


# TODO: Leverage Sphinx for parsing, but provide a fallback?
def extract_documentation(function):
    """
    :type function: types.FunctionType
    :rtype: tuple<
        None | six.text_type,
        dict<six.text_type, six.class_types>,
        dict<six.text_type, six.text_type>>
    :raise AmbiguousParamDesc:
    :raise AmbiguousParamType:
    :raise UndefinedParamDesc:
    """

    global inspect
    if inspect is None: # pragma: no cover
        import inspect

    data_types = {}
    descriptions = {}
    docstring = inspect.getdoc(function)

    if docstring is None:
        return (None, data_types, descriptions)

    global docutils
    if docutils is None: # pragma: no cover
        import docutils.core
        import docutils.nodes

    global six
    if six is None: # pragma: no cover
        import six

    doc = docutils.core.publish_doctree(docstring)

    for field in doc.traverse(docutils.nodes.field):
        [field_name] = field.traverse(docutils.nodes.field_name)
        directive = re.match(r'^(\w+)\s+([^\s]*)$', field_name.astext())

        if directive is None:
            continue

        (kind, name) = directive.groups()
        name = six.text_type(name)

        field_body = field.traverse(docutils.nodes.paragraph)

        if len(field_body) == 0:
            field_body = None
        else:
            [field_body] = field_body
            field_body = field_body.astext()

        if kind == 'param':
            if name in descriptions:
                raise AmbiguousParamDesc(name)
            elif field_body is None:
                raise UndefinedParamDesc(name)
            else:
                descriptions[name] = six.text_type(field_body)
        elif kind == 'type':
            if name in data_types:
                raise AmbiguousParamDataType(name)
            elif field_body is None:
                raise UndefinedParamDataType(name)
            else:
                data_types[name] = load_type(
                    field_body,
                    inspect.getmodule(function))

    main_desc = doc.traverse(lambda node:
        isinstance(node, docutils.nodes.paragraph) and (node.parent is doc))
    
    if len(main_desc) == 0:
        main_desc = None
    else:
        [main_desc] = main_desc
        main_desc = six.text_type(main_desc.astext())

    return (main_desc, data_types, descriptions)


# TODO: Support list options? Via type `list`? Via varargs?
# TODO: Support sub-commands via enum parameters?
def extract_parameters(function):
    """
    :type function: types.FunctionType
    :rtype: list<six.text_type | tuple<six.text_type, object>>
    :raise DynamicArgs:
    :raise TupleArg:
    """

    global inspect
    if inspect is None: # pragma: no cover
        import inspect

    arg_spec = inspect.getargspec(function)

    if (arg_spec.varargs is not None) or (arg_spec.keywords is not None):
        raise DynamicArgs()

    nr_kwargs = 0 if arg_spec.defaults is None else len(arg_spec.defaults)
    kwargs_offset = len(arg_spec.args) - nr_kwargs
    params = []

    global six
    if six is None: # pragma: no cover
        import six

    for name, arg_i in zip(arg_spec.args, range(len(arg_spec.args))):
        if not isinstance(name, six.string_types):
            raise TupleArg(name)

        name = six.text_type(name)
        kwarg_i = arg_i - kwargs_offset
        is_keyword = (0 <= kwarg_i < nr_kwargs)

        if is_keyword:
            params.append((name, arg_spec.defaults[kwarg_i]))
        else:
            params.append(name)

    return params


# TODO: Support parameterized types? E.g. list<str>
def load_type(name, at_module):
    """
    :type name: six.text_type
    :type at_module: types.ModuleType
    :rtype: six.class_types
    """

    global six
    if six is None: # pragma: no cover
        import six

    module = at_module
    parts = name.split('.')
    (parts, attributes) = (parts[:-1], parts[-1:])

    while len(parts) > 0:
        try:
            module = __import__('.'.join(parts))
        except ImportError:
            attributes.insert(0, parts.pop())
        else:
            break

    for data_type in (module, six.moves.builtins):
        for attribute in attributes:
            try:
                data_type = getattr(data_type, attribute)
            except AttributeError:
                break
        else:
            global inspect
            if inspect is None: # pragma: no cover
                import inspect

            if inspect.isclass(data_type):
                return data_type

    raise UnknownParamDataType(name)


# TODO: Add a version argument from `__version__`?
def start(main,
        args = None,
        arg_parser = None,
        soft_errors = True):
    
    """
    Starts a function with program arguments parsed via :py:mod:`argparse`.

    :type main: types.FunctionType
    :param main: entry point function
    :type args: list<six.text_type>
    :param args: user defined program arguments, otherwise leaves it up to
        :py:meth:`argparse.ArgumentParser.parse_args` to define
    :type arg_parser: argparse.ArgumentParser
    :param arg_parser: user defined argument parser
    :type soft_errors: bool
    :param soft_errors: if ``True``, catches conversion and parsing
        exceptions and passes them as error messages for
        :py:meth:`argparse.ArgumentParser.error`
    :return: entry point's return value
    """

    if arg_parser is None:
        global argparse
        if argparse is None: # pragma: no cover
            import argparse

        arg_parser = argparse.ArgumentParser(
            formatter_class = argparse.ArgumentDefaultsHelpFormatter)

    try:
        (description, arguments) = extract_arguments(main)

        if description is not None:
            if arg_parser.description is None:
                arg_parser.description = description
            else:
                raise AmbiguousDesc()

        for argument in arguments:
            argument.add_to_parser(arg_parser)
    except Error as error:
        if soft_errors:
            arg_parser.error(error)
        else:
            raise
    else:
        return main(**vars(arg_parser.parse_args(args = args)))
