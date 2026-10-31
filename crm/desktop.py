"""Supervisor do painel/worker e instalação da tarefa do Windows."""
import base64
import os
import signal
import subprocess
import sys
import time
from contextlib import contextmanager
from pathlib import Path


TASK_NAME = 'Vertice CRM2 Brasil'
TASK_MARKER = 'Gerenciado por hello/iniciar.py - exclusivo do CRM 2 Brasil'


@contextmanager
def instance_lock(path):
    path.parent.mkdir(exist_ok=True)
    handle = path.open('a+b')
    acquired = False
    try:
        handle.seek(0, 2)
        if handle.tell() == 0:
            handle.write(b'0')
            handle.flush()
        handle.seek(0)
        try:
            if os.name == 'nt':
                import msvcrt
                msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl
                fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            acquired = True
        except OSError:
            yield False
            return
        yield True
    finally:
        if acquired:
            handle.seek(0)
            if os.name == 'nt':
                import msvcrt
                msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                import fcntl
                fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
        handle.close()


def interpreter(root):
    candidate = root / '.venv' / ('Scripts/python.exe' if os.name == 'nt' else 'bin/python')
    return str(candidate if candidate.is_file() else Path(sys.executable))


def child_commands(root, python, port=8502, panel=True):
    commands = {'automacao': [python, '-m', 'crm.local_runner']}
    if panel:
        commands['painel'] = [python, '-m', 'streamlit', 'run', str(root / 'streamlit_app.py'),
                             '--server.address', '127.0.0.1', '--server.port', str(port),
                             '--server.headless', 'true', '--browser.gatherUsageStats', 'false']
    return commands


def supervise(root, port=8502, panel=True):
    python = interpreter(root)
    with instance_lock(root / 'data' / 'crm2-runner.lock') as owned:
        if not owned:
            print('O CRM 2 já está em execução nesta pasta. Não foi iniciada outra cópia.', flush=True)
            return
        commands = child_commands(root, python, port, panel)
        children, failures = {}, {name: [] for name in commands}
        env = {**os.environ, 'PYTHONUNBUFFERED': '1', 'PYTHONUTF8': '1'}
        print(f'CRM 2: painel Streamlit na porta {port}; rotina local ativa. Logs: data/automation.log.', flush=True)
        print('A automação não ativa campanhas pausadas e não envia fora de 09h–10h de Brasília. Ctrl+C encerra somente o CRM 2.', flush=True)
        try:
            while True:
                for name, cmd in commands.items():
                    process = children.get(name)
                    if process is None or process.poll() is not None:
                        failures[name] = [x for x in failures[name] if time.monotonic() - x < 300]
                        if len(failures[name]) >= 3:
                            continue
                        if process is not None:
                            print(f'CRM 2: processo {name} encerrou; tentando reiniciar sem remover reservas do banco.', flush=True)
                        flags = subprocess.CREATE_NEW_PROCESS_GROUP if os.name == 'nt' else 0
                        children[name] = subprocess.Popen(cmd, cwd=root, env=env, creationflags=flags)
                        failures[name].append(time.monotonic())
                if children and all(p.poll() is not None for p in children.values()):
                    print('Os processos do CRM 2 pararam. Confira as mensagens e a configuração local.', flush=True)
                    return
                time.sleep(2)
        except KeyboardInterrupt:
            print('Encerrando o CRM 2; aguardando concluir a operação corrente...', flush=True)
        finally:
            for process in children.values():
                if process.poll() is None:
                    try:
                        process.send_signal(signal.CTRL_BREAK_EVENT) if os.name == 'nt' else process.terminate()
                    except OSError:
                        pass
            for process in children.values():
                try:
                    process.wait(timeout=45)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait()


def powershell_registration(root, python):
    def quote(value):
        return "'" + str(value).replace("'", "''") + "'"
    # list2cmdline é a regra de escape do próprio Windows para caminhos com espaços.
    arguments = subprocess.list2cmdline([str(root / 'iniciar.py')])
    return f"""$ErrorActionPreference = 'Stop'
$name = {quote(TASK_NAME)}
$marker = {quote(TASK_MARKER)}
$old = Get-ScheduledTask -TaskName $name -ErrorAction SilentlyContinue
if ($old -and $old.Description -ne $marker) {{ throw 'Ja existe outra tarefa com esse nome. Nenhuma tarefa foi alterada.' }}
$action = New-ScheduledTaskAction -Execute {quote(python)} -Argument {quote(arguments)} -WorkingDirectory {quote(root)}
$daily = New-ScheduledTaskTrigger -Daily -At '08:50'
$logon = New-ScheduledTaskTrigger -AtLogOn -User ([System.Security.Principal.WindowsIdentity]::GetCurrent().Name)
$options = New-ScheduledTaskSettingsSet -StartWhenAvailable -WakeToRun -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -MultipleInstances IgnoreNew -ExecutionTimeLimit ([TimeSpan]::Zero) -RestartCount 3 -RestartInterval (New-TimeSpan -Minutes 1)
$principal = New-ScheduledTaskPrincipal -UserId ([System.Security.Principal.WindowsIdentity]::GetCurrent().Name) -LogonType Interactive -RunLevel Limited
Register-ScheduledTask -TaskName $name -Description $marker -Action $action -Trigger @($daily,$logon) -Settings $options -Principal $principal -Force | Out-Null
Start-ScheduledTask -TaskName $name
Write-Output 'CRM 2: tarefa instalada para 08h50 e logon. Inicio solicitado. Nenhuma tarefa do CRM principal foi alterada.'
"""


def install_windows(root):
    if os.name != 'nt':
        raise RuntimeError('A instalação automática é para o Windows. Neste sistema use python iniciar.py.')
    script = powershell_registration(root, interpreter(root))
    encoded = base64.b64encode(script.encode('utf-16le')).decode('ascii')
    result = subprocess.run(['powershell.exe', '-NoProfile', '-NonInteractive', '-EncodedCommand', encoded],
                            capture_output=True, text=True, errors='replace')
    if result.returncode:
        print('O Windows não confirmou a instalação da tarefa. Verifique as permissões do Agendador de Tarefas para seu usuário; o CRM principal não foi alterado.')
        raise SystemExit(1)
    print('Tarefa Vertice CRM2 Brasil instalada e início solicitado. Ela roda no logon e diariamente às 08h50 do relógio do Windows.', flush=True)
    print('Mantenha o relógio do Windows em Brasília, o PC ligado/conectado e o usuário logado. A tarefa pode acordar da suspensão se o Windows permitir; não liga um PC desligado.', flush=True)
