# Copyright (c) 2018, Ioannis Tziakos
# All rights reserved.
import subprocess
import os
import re
import sys

from tox import hookimpl, exception
from tox.venv import VirtualEnv


def env_exists(edm, envname):
    try:
        subprocess.check_call([str(edm), 'envs', 'exists', envname])
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
            'TOX-EDM cannot infer version from {!r}'.format(name))
    edm = venv.getcommandpath('edm', venv=False)
    action.venv.envconfig.whitelist_externals.append(
        os.path.dirname(edm))
    if action.activity == 'recreate':
        action.popen([
            edm, 'envs', 'create', action.venvname,
            '--force', '--version', version])
    elif not env_exists(edm, action.venvname):
        action.popen([
            edm, 'envs', 'create', action.venvname,
            '--version', version])

    prefix = action.popen(
        [edm, 'prefix', '-e', action.venvname],
        redirect=False, returnout=True)
    prefix = prefix.strip()
    # The envbindir will be used to find the environment python
    # So we have to make sure that it has the right value.
    action.venv.envconfig.envbindir = prefix
    action.venv.envconfig.whitelist_externals.append(prefix)
    return True


@hookimpl
def tox_testenv_install_deps(venv, action):
    deps = venv._getresolvedeps()
    name = action.venvname
    if len(deps) > 0:
        edm = venv.getcommandpath('edm', venv=False)
        depinfo = " ".join(map(str, deps))
        action.setactivity("installdeps", "%s" % depinfo)
        args = [edm, 'install', '-e', name, '-y'] + map(str, deps)
        action.popen(args)
    return True


@hookimpl
def tox_runenvreport(venv, action):
    edm = venv.getcommandpath('edm', venv=True)
    output = action.popen([
        edm, 'run', '-e', action.venvname, '--',
        'pip', 'freeze'])
    output = output.split("\n\n")[-1]
    return output.strip().splitlines()


@hookimpl
def tox_runtest_pre(venv):
    return True


@hookimpl
def tox_runtest_post(venv):
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
        env = venv._getenv(testcommand=True)
        cwd = envconfig.changedir
        edm = venv.getcommandpath('edm', venv=True)
        # Display PYTHONHASHSEED to assist with reproducibility.
        action.setactivity(
            "runtests", "PYTHONHASHSEED={!r}".format(
                env.get("PYTHONHASHSEED")))
        for i, argv in enumerate(envconfig.commands):
            message = "commands[%s] | %s" % (
                i, ' '.join([str(x) for x in argv]))
            action.setactivity("runtests", message)
            # check to see if we need to ignore the return code
            # if so, we need to alter the command line arguments
            ignore_return = argv[0].startswith("-")
            if ignore_return:
                if argv[0] == "-":
                    del argv[0]
                else:
                    argv[0] = argv[0].lstrip("-")
            argv = [edm, 'run', '-e', action.venvname, '--'] + argv
            try:
                action.popen(
                    argv, cwd=cwd, env=env, redirect=redirect,
                    ignore_ret=ignore_return)
            except exception.InvocationError as err:
                if envconfig.ignore_outcome:
                    msg = "command failed but result from testenv is ignored\ncmd:"
                    session.report.warning("{} {}".format(msg, err))
                    venv.status = "ignored failed command"
                    continue  # keep processing commands

                session.report.error(str(err))
                venv.status = "commands failed"
                if not envconfig.ignore_errors:
                    break  # Don't process remaining commands
            except KeyboardInterrupt:
                venv.status = "keyboardinterrupt"
                session.report.error(venv.status)
                raise
    return True


@hookimpl
def tox_get_python_executable(envconfig):
    venv = VirtualEnv(envconfig=envconfig)
    edm = venv.getcommandpath('edm', venv=False)
    if env_exists(edm, envconfig.envname):
        executable = subprocess.check_output([
            str(edm), 'run', '-e', envconfig.envname, '--',
            'python', '-c',
            "import sys; sys.stdout.write(sys.executable)"])
        executable = executable.strip()
        if sys.platform.startswith('win'):
            # Make sure that we always have the right bin directory
            envconfig.envbindir = os.path.join(
                os.path.dirname(executable), 'Scripts')
        return os.path.abspath(executable)
    else:
        return None
