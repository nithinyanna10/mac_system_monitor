"""
Command-line interface for Mac System Monitor: dashboard, API, collect (JSON/watch).
"""
from __future__ import annotations

import argparse
import json
import sys
import time


def cmd_collect(args: argparse.Namespace) -> int:
    from metrics import collect, collect_full
    full = getattr(args, "full", False)
    m = collect_full() if full else collect()
    if args.json:
        out = m.to_dict()
        print(json.dumps(out, indent=2 if args.pretty else None))
        return 0
    if m.error:
        print(m.error, file=sys.stderr)
        return 1
    if args.watch:
        try:
            import os
            while True:
                os.system("clear" if os.name != "nt" else "cls")
                m = collect_full() if full else collect()
                if args.json:
                    print(json.dumps(m.to_dict()))
                else:
                    print(f"CPU: {m.cpu_percent:.1f}%  Memory: {m.memory_percent:.1f}%  Disk: {m.disk_percent:.1f}%  Uptime: {m.uptime_sec:.0f}s")
                time.sleep(args.interval)
        except KeyboardInterrupt:
            pass
        return 0
    # Default: run metrics.py main (rich output)
    from metrics import main as metrics_main
    metrics_main()
    return 0


def cmd_dashboard(args: argparse.Namespace) -> int:
    import subprocess
    cmd = [sys.executable, "-m", "streamlit", "run", "dashboard.py", "--server.headless", "true"]
    if getattr(args, "port", None):
        cmd.extend(["--server.port", str(args.port)])
    subprocess.run(cmd)
    return 0


def cmd_api(args: argparse.Namespace) -> int:
    try:
        import uvicorn
    except ImportError:
        print("Install uvicorn: pip install uvicorn", file=sys.stderr)
        return 1
    try:
        from config import API_HOST, API_PORT
    except ImportError:
        API_HOST, API_PORT = "0.0.0.0", 8765
    port = getattr(args, "port", None) or API_PORT
    uvicorn.run("api:app", host=API_HOST, port=port, reload=bool(getattr(args, "reload", False)))
    return 0


def cmd_validate_config(args: argparse.Namespace) -> int:
    from config import get, load_config_file, DEFAULTS
    loaded = load_config_file()
    print("Config file loaded:", loaded)
    for key in ["dashboard.refresh_default_sec", "alerts.cpu_percent", "api.port"]:
        print(f"  {key}: {get(key)}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(prog="mac_system_monitor", description="Mac System Monitor CLI")
    sub = parser.add_subparsers(dest="command", required=True)

    p_collect = sub.add_parser("collect", help="Collect metrics once (rich output) or --json")
    p_collect.add_argument("--json", action="store_true", help="Output JSON")
    p_collect.add_argument("--pretty", action="store_true", help="Pretty-print JSON")
    p_collect.add_argument("--full", action="store_true", help="Include processes, network, disk mounts")
    p_collect.add_argument("--watch", action="store_true", help="Watch mode (refresh every N sec)")
    p_collect.add_argument("--interval", type=float, default=2.0, help="Watch interval seconds")
    p_collect.set_defaults(run=cmd_collect)

    p_dash = sub.add_parser("dashboard", help="Run Streamlit dashboard")
    p_dash.add_argument("--port", type=int, default=None, help="Port")
    p_dash.set_defaults(run=cmd_dashboard)

    p_api = sub.add_parser("api", help="Run REST API server")
    p_api.add_argument("--port", type=int, default=None, help="Port")
    p_api.add_argument("--reload", action="store_true", help="Reload on change")
    p_api.set_defaults(run=cmd_api)

    p_validate = sub.add_parser("validate-config", help="Validate and show config")
    p_validate.set_defaults(run=cmd_validate_config)

    args = parser.parse_args()
    return args.run(args)


if __name__ == "__main__":
    sys.exit(main())
