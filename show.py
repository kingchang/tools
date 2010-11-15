#!/usr/bin/env python
# -*- coding: utf-8 -*-


# TODO: Use a percentage of the current terminal height instead of a fixed
#       number of lines.
# TODO: Clean up (abstract logic behind classes e.g. Pager, LessPager, etc).
# TODO: Handle the KeyboardInterrupt exception gracefully.
# TODO: Detect missing programs and provide automatic installation or fallbacks.
# TODO: Guess input syntax even if already colored to use an appropriate pager.
# TODO: Pass real files to Kompare instead of diff output?
# TODO: Allow override of the default diff pager program (e.g. opendiff kdiff3
#       tkdiff xxdiff meld kompare gvimdiff diffuse ecmerge p4merge araxis
#       emerge vimdiff).


# Standard library:
import codecs, locale, re, subprocess, sys

try:
    import argparse
except ImportError as error:
    sys.exit('Python 2.7 or newer is required: %s' % error)

# External modules:
try:
    import pygments, pygments.formatters, pygments.lexers
except ImportError as error:
    sys.exit('Pygments is required, see <http://pygments.org/>: %s' % error)


class Arguments (argparse.ArgumentParser):
    def __init__(self):
        super(Arguments, self).__init__(description = '''
            Smart pager with automatic syntax highlighting and diff support.''')
        
        def natural(value):
            number = int(value, 10)
            
            if number < 0:
                raise argparse.ArgumentTypeError('%d is not a natural number'
                    % value)
            
            return number
        
        arguments = [
            ('-l', {
                'dest': 'lines',
                'default': 15,
                'type': natural,
                'help': 'Number of lines to display inline before paging.',
            }),
            ('-L', {
                'dest': 'label',
                'action': 'append',
                'help': '(diff)',
            }),
            ('-p', {
                'dest': 'pager',
                'action': 'append',
                'help': 'Custom pager program to use and arguments.',
            }),
            ('-u', {
                'action': 'store_true',
                'default': True,
                'help': '(diff)',
            }),
            ('file', {
                'nargs': '?',
                'default': sys.stdin,
                'type': argparse.FileType(),
                'help': 'File to be shown, otherwise use standard input.',
            }),
            ('file2', {
                'nargs': '?',
                'type': argparse.FileType(),
                'help': 'File to be compared against, and switch to diff mode.',
            }),
            ('git', {
                'nargs': '*',
                'help': 'Assume git diff arguments, and switch to diff mode.',
            }),
        ]
        
        for name, options in arguments:
            self.add_argument(name, **options)
    
    
    def parse_args(self):
        args = super(Arguments, self).parse_args()
        
        if len(args.git) == 5:
            self._parse_git_diff_arguments(args)
        
        if args.file2 is None:
            args.diff_mode = False
        else:
            args.diff_mode = True
            self._parse_diff_arguments(args)
        
        return args
    
    
    def _parse_diff_arguments(self, args):
        files = [args.file, args.file2]
        diff = ['diff']
        
        if args.u:
            diff.append('-u')
        
        if args.label is None:
            args.label = [file.name for file in files]
        
        for label in args.label:
            # Kompare chokes on tab characters in labels.
            diff.extend(['-L', label.replace('\t', ' ')])
        
        if args.file2 is sys.stdin:
            # Compare standard input with given file, not the other way around.
            files.reverse()
        
        for file in files:
            diff.append('-' if file is sys.stdin else file.name)
        
        args.file = subprocess.Popen(diff, stdout = subprocess.PIPE).stdout
    
    
    def _parse_git_diff_arguments(self, args):
        (path, old_file) = (args.file, args.file2)
        (old_hex, old_mode, new_file, new_hex, new_mode) = args.git
        
        (args.file, args.file2) = (old_file, path)
        args.label = [path.name + ' (%s)' % h for h in [old_hex, new_hex]]


def display(stream, text, lexer, formatter):
    if lexer is not None:
        text = pygments.highlight(text, lexer, formatter)
    
    stream.write(text)


def guess_lexer(file_name, text):
    # Detect ANSI "color" escape sequences.
    if re.search(r'\x1B\[\d+(;\d+)*m', text):
        return None
    
    try:
        lexer = pygments.lexers.guess_lexer_for_filename(file_name, text)
    except pygments.util.ClassNotFound:
        lexer = pygments.lexers.guess_lexer(text)
    
    lexer.add_filter('codetagify')
    return lexer


def locale_writer(stream):
    return codecs.getwriter(locale.getpreferredencoding())(stream)


args = Arguments().parse_args()
formatter = pygments.formatters.Terminal256Formatter()
lexer = pygments.lexers.DiffLexer() if args.diff_mode else None
pager = None
lines = []

for line in args.file:
    if pager is not None:
        display(pager.stdin, line, lexer, formatter)
        continue
    
    lines.append(line)
    
    if len(lines) >= args.lines:
        text = ''.join(lines)
        
        if lexer is None:
            lexer = guess_lexer(args.file.name, text)
        
        if args.pager is None:
            if isinstance(lexer, pygments.lexers.DiffLexer):
                args.pager = ['kompare', '-o', '-']
                lexer = None
            else:
                args.pager = ['less', '-cRx4']
        
        pager = subprocess.Popen(args.pager, stdin = subprocess.PIPE)
        pager.stdin = locale_writer(pager.stdin)
        display(pager.stdin, text, lexer, formatter)

if pager is not None:
    pager.communicate()
    pager.stdin.close()
    pager.wait()
elif len(lines) > 0:
    text = ''.join(lines)
    lexer = guess_lexer(args.file.name, text)
    display(locale_writer(sys.stdout), text, lexer, formatter)

args.file.close()
