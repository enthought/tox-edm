# Copyright (c) 2018, Ioannis Tziakos
# All rights reserved.
import subprocess
import os
import re

from tox import hookimpl, exception


def edm(*parameters, **kw):
    return subprocess.check_output(
        ['edm'] + list(parameters), shell=True, **kw)


def env_exists(envname):
    try:
        subprocess.check_call(['edm', 'envs', 'exists', envname], shell=True)
    except subprocess.CalledProcessError:
        return False
    else:
        return True


@hookimpl
def tox_testenv_create(venv, action):
    name = venv.envconfig.basepython
    m = re.match(r"python(\d)\.(\d)", name)
    if m:
        version = "%s.%s" % m.groups()
    else:
        raise exception.UnsupporterInterpreter(
            'EDM cannot infer version from {!r}'.format(name))
    if action.activity == 'recreate':
        edm(
            'envs', 'create', action.venvname,
            '--force', '--version', version)
    else:
        if not env_exists(action.venvname):
            edm('envs', 'create', action.venvname, '--version', version)
    prefix = edm('prefix', '-e', action.venvname)
    action.venv.envconfig.whitelist_externals.append(prefix)
    return True


@hookimpl
def tox_testenv_install_deps(venv, action):
    deps = venv._getresolvedeps()
    name = action.venvname
    if deps:
        depinfo = " ".join(map(str, deps))
        action.setactivity("installdeps", "%s" % depinfo)
        edm('install', '-e', name, '-y', *map(str, deps))
    return True

@hookimpl
def tox_runenvreport(venv, action):
    packages = edm(
        'run', '-e', action.venvname, '--',
        'pip', 'freeze')
    print packages.splitlines()
    return packages.splitlines()

@hookimpl
def tox_runtest_pre(venv):
    print 'PRE'
    return True

@hookimpl
def tox_runtest_post(venv):
    print 'POST'
    return True

@hookimpl
def tox_runtest(venv, redirect):
    session = venv.session
    envconfig = venv.envconfig
    action = session.newaction(venv, "runtests")
    with action:
        venv.status = 0
        session.make_emptydir(envconfig.envtmpdir)
        envconfig.envtmpdir.ensure(dir=1)
        cwd = envconfig.changedir
        env = venv._getenv(testcommand=True)
        for i, argv in enumerate(envconfig.commands):
            message = "commands[%s] | %s" % (
                i, ' '.join([str(x) for x in argv]))
            action.setactivity("runtests", message)
            output = edm('run', '-e', action.venvname, '--', *argv, env=env)
    return True

@hookimpl
def tox_get_python_executable(envconfig):
    if env_exists(envconfig.envname):
        executable = edm(
            'run', '-e', envconfig.envname, '--',
            'python', '-c', "import sys; sys.stdout.write(sys.executable)")
        return os.path.abspath(executable)
    else:
        return None
