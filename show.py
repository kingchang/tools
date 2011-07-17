#!/usr/bin/env python
# -*- coding: UTF-8 -*-


# Standard library:
from __future__ import unicode_literals
import errno, os, sys


# No abstract base class for performance.
class StreamInput:
    def __init__(self, stream, name, line = 1):
        self.line = line
        self.name = name
        self.stream = stream
    
    
    def close(self):
        self.stream.close()


class FileInput (StreamInput):
    def __init__(self, path):
        StreamInput.__init__(self, open(path), name = os.path.abspath(path))


class SubProcessInput (StreamInput):
    def __init__(self, args, **kargs):
        import subprocess
        
        process = subprocess.Popen(args,
            close_fds = True,
            stderr = open(os.devnull),
            stdout = subprocess.PIPE)
        
        if process.wait() != 0:
            # No error message for performance, since it isn't shown anyway.
            raise IOError()
        
        StreamInput.__init__(self, stream = process.stdout, **kargs)
        self._process = process
    
    
    def close(self):
        self._process.communicate()
        StreamInput.close(self)


class DirectoryInput (SubProcessInput):
    def __init__(self, path, ls_args):
        SubProcessInput.__init__(self, ['ls'] + ls_args,
            name = os.path.abspath(path))


class PerlDocInput (SubProcessInput):
    def __init__(self, module):
        SubProcessInput.__init__(self, ['perldoc', '-t', module],
            name = module)


class UriInput (StreamInput):
    def __init__(self, uri, default_protocol):
        import urllib, urlparse
        parts = urlparse.urlparse(uri)
        
        if parts.scheme == '':
            clean_uri = urllib.unquote(parts.path)
            clean_parts = urlparse.urlparse(clean_uri)
            
            if clean_parts.path == parts.path:
                uri = default_protocol + uri
            elif clean_parts.scheme == '':
                uri = default_protocol + clean_uri
            else:
                uri = clean_uri
        
        StreamInput.__init__(self, urllib.urlopen(uri), name = uri)


class Options:
    # TODO: Too long, refactor.
    def __init__(self,
            default_protocol = 'http://',
            self_path = sys.argv[0],
            self_repr = 'self',
            stdin_stream = sys.stdin,
            stdin_repr = '-',
            terminal_only = False):
        
        # argparse isn't used for performance.
        import getopt
        
        try:
            # No long options available for performance.
            (options, arguments) = getopt.getopt(sys.argv[1:], 'f:hi:l:m:p:s:t')
        except getopt.GetoptError as error:
            sys.exit(str(error))
        
        self.default_protocol = default_protocol
        self.ls_arguments = []
        self.self_path = self_path
        self.self_repr = self_repr
        self.stdin_stream = stdin_stream
        self.stdin_repr = stdin_repr
        self.terminal_only = terminal_only
        
        if len(arguments) > 2:
            options.append(('-h', ''))
        
        for option, value in options:
            if option == '-h':
                print '''
Automatic pager with syntax highlighting, diff support and file/text search.

Usage:
  pager     [options] [input-1 [input-2]]
  search    [options] [input]*

Options:
  -f        list files with names matching the given pattern
  -h        show usage help
  -i        standard input string representation, defaults to "%s"
  -l        option for "ls", when listing directories
  -m        list file matches for the given pattern
  -p        protocol for URI's with missing scheme, defaults to "%s"
  -s        this script's path string representation, defaults to "%s"
  -t        use terminal only, no graphical interfaces

An input can be a path, an URI, a Perl module name, standard input or this script's (given their string representation). If given a directory, its' contents are listed via "ls".

The input's name can also be suffixed with a colon followed by a line number to scroll to, if possible.
'''.strip() % (stdin_repr, default_protocol, self_repr)
                sys.exit()
            elif option == '-i':
                self.stdin_repr = value
            if option == '-l':
                self.ls_arguments.append(value)
            elif option == '-p':
                self.default_protocol = value
            elif option == '-s':
                self.self_repr = value
            elif option == '-t':
                self.terminal_only = True
        
        if len(arguments) == 2:
            self.input = self._open_diff_input(map(self._open_input, arguments))
        else:
            self.diff_mode = False
            
            if len(arguments) == 0:
                if self.stdin_stream.isatty():
                    self.input = self._open_input(os.curdir)
                else:
                    self.input = StreamInput(self.stdin_stream,
                        name = self.stdin_repr)
            elif len(arguments) == 1:
                inputs = []
                
                if not self.stdin_stream.isatty():
                    inputs.append(StreamInput(self.stdin_stream,
                        name = self.stdin_repr))
                
                inputs.append(self._open_input(arguments[0]))
                
                if len(inputs) > 1:
                    self.input = self._open_diff_input(inputs)
                else:
                    [self.input] = inputs
    
    
    def _open_diff_input(self, inputs):
        import difflib, cStringIO
        
        labels = [input.name for input in inputs]
        header = b'diff -u %s %s' % tuple(labels)
        
        diff = cStringIO.StringIO(
            header + b'\n' + b''.join(difflib.unified_diff(
                inputs[0].stream.readlines(),
                inputs[1].stream.readlines(),
                *labels)))
        
        self.diff_mode = True
        return StreamInput(diff, name = header)
    
    
    # TODO: Too long, refactor.
    def _open_input(self, path):
        try:
            return FileInput(path)
        except IOError as error:
            # Check common and fail-fast cases first for performance.
            
            if error.errno == errno.EISDIR:
                return DirectoryInput(path, self.ls_arguments)
            
            if error.errno == errno.ENOENT:
                if path == self.stdin_repr:
                    return StreamInput(self.stdin_stream,
                        name = self.stdin_repr)
                
                try:
                    return PerlDocInput(path)
                except IOError:
                    pass
                
                if path == self.self_repr:
                    return FileInput(self.self_path)
                
                import httplib
                
                try:
                    return UriInput(path, self.default_protocol)
                except httplib.InvalidURL:
                    pass
                except IOError as uri_error:
                    if uri_error.filename is not None:
                        import urlparse
                        parts = urlparse.urlparse(path)
                        
                        try:
                            return self._open_input(parts.path)
                        except IOError:
                            pass
                
                import re
                
                go_to_line = re.search(
                    r'^ (.+?) : ([+-]? (?: [1-9] | \d{2,})) $', path,
                    re.VERBOSE)
                
                if go_to_line is not None:
                    (path, line) = go_to_line.groups()
                    
                    try:
                        stream = self._open_input(path)
                        stream.line = int(line)
                        return stream
                    except IOError:
                        pass
            
            raise error


if __name__ == '__main__':
    options = Options()
    options.input.close()
