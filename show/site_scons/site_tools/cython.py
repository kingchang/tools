# -*- coding: UTF-8 -*-


PROGRAM = 'cython'


def build(env, target, source, is_standalone = False, do_compilation = False):
    embed = ['--embed'] if is_standalone else []
    
    command = env.Command(target, source,
        [[PROGRAM, '--output-file', str(target)] + embed + map(str, source)])
    
    if do_compilation:
        env.ParseConfig(['python-config', '--cflags', '--libs'])
        return env.Program(target)
    else:
        return command


def exists(env):
    return env.Detect(PROGRAM)


def generate(env):
    env.AddMethod(build, PROGRAM.title())
