# PTY Recovery (macOS forkpty)

If your terminal shows:

- `forkpty: Device not configured`
- `未能创建新的进程和打开伪终端(pseudo-tty)`

It usually means macOS cannot allocate a pseudo-terminal (PTY). This is unrelated to the project code.

## Non-terminal ways to run Gatekeeper

### Option A: Run from an IDE

Open and run:

- `standalone_workspace/scripts/gatekeeper_report_runner.py`

It prints the log file path under:

- `standalone_workspace/tests/qa_reports/`

### Option B: Automator (no interactive terminal)

Create an Automator “Application” with one action: “Run Shell Script”.

Shell: `/bin/zsh`

Script (replace `<REPO_ROOT>`):

```sh
cd "<REPO_ROOT>"
/usr/bin/python3 standalone_workspace/scripts/gatekeeper_report_runner.py
```

## System recovery checklist

1. Reboot macOS.
2. If the issue persists, check if this is a managed (MDM) device.
3. Temporarily disable security tools that may block PTY allocation.
4. If you can run CI, rely on GitHub Actions workflow:
   - `.github/workflows/self_proving_gatekeeper.yml`
