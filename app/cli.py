"""
ILLIP AI CLI — install via: pip install illip-ai
Usage:
  illip start              — start the server
  illip start --host 0.0.0.0 --port 8000
  illip start --reload     — dev mode with auto-reload
  illip status             — check if server is running
  illip version            — print version
"""

import sys


def main():
    try:
        import click
    except ImportError:
        print("Run: pip install click")
        sys.exit(1)

    import click  # noqa: F811

    @click.group()
    def cli():
        """ILLIP AI — your AI company, in your device."""
        pass

    @cli.command()
    @click.option("--host", default=None, help="Bind host (default from .env or 127.0.0.1)")
    @click.option("--port", default=None, type=int, help="Port (default from .env or 8000)")
    @click.option("--reload", is_flag=True, help="Dev mode: auto-reload on file changes")
    @click.option("--workers", default=1, type=int, help="Number of worker processes")
    def start(host, port, reload, workers):
        """Start the ILLIP AI server."""
        try:
            import uvicorn
        except ImportError:
            click.echo("Run: pip install uvicorn[standard]")
            sys.exit(1)

        from app.config import settings
        _host = host or settings.api_host
        _port = port or settings.api_port
        click.echo(f"Starting ILLIP AI v{_get_version()} on http://{_host}:{_port}")
        click.echo("Press Ctrl+C to stop.")
        uvicorn.run(
            "app.main:app",
            host=_host,
            port=_port,
            reload=reload,
            workers=1 if reload else workers,
            log_level="info",
        )

    @cli.command()
    def status():
        """Check if ILLIP AI server is running."""
        try:
            import httpx
        except ImportError:
            click.echo("Run: pip install httpx")
            sys.exit(1)

        from app.config import settings
        url = f"http://{settings.api_host}:{settings.api_port}/api/health"
        try:
            r = httpx.get(url, timeout=3)
            d = r.json()
            click.echo(f"ILLIP AI: {d.get('status', 'unknown')} — provider: {d.get('provider', '?')}")
        except Exception:
            click.echo(f"ILLIP AI not reachable at {url}. Run: illip start")
            sys.exit(1)

    @cli.command()
    def version():
        """Print version."""
        click.echo(f"ILLIP AI {_get_version()}")

    @cli.command()
    def setup():
        """Install dependencies and create .env from .env.example."""
        import subprocess
        from pathlib import Path
        click.echo("Installing dependencies...")
        subprocess.run([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"], check=True)
        env = Path(".env")
        if not env.exists():
            example = Path(".env.example")
            if example.exists():
                env.write_text(example.read_text())
                click.echo(".env created from .env.example — edit it to configure your model provider.")
            else:
                click.echo("No .env.example found. Create a .env manually.")
        else:
            click.echo(".env already exists.")
        click.echo("Done. Run: illip start")

    def _get_version():
        try:
            from app import __version__
            return __version__
        except Exception:
            return "unknown"

    cli()


if __name__ == "__main__":
    main()
