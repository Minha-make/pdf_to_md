"""Command Line Interface (CLI) for OmniPDF2MD."""

import sys
import threading
import urllib.request
import webbrowser
from pathlib import Path
from typing import Annotated

import pymupdf as fitz
import typer
import uvicorn
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from omnipdf import __version__
from omnipdf.config import settings
from omnipdf.core.inspector import inspect_pdf
from omnipdf.core.models import (
    ConversionConfig,
    ConversionMode,
    EncryptedPDFError,
)
from omnipdf.core.router import convert_pdf

app = typer.Typer(
    name="omnipdf",
    help="OmniPDF2MD — Local Universal PDF-to-Markdown Converter",
    add_completion=False,
)
console = Console()


@app.command("convert")
def convert(
    input_path: Annotated[Path, typer.Argument(help="Path to input PDF file")],
    output_dir: Annotated[
        Path,
        typer.Option("-o", "--output", help="Directory to save converted Markdown and assets"),
    ] = Path("output"),
    mode: Annotated[
        str, typer.Option("--mode", "-m", help="Conversion mode: auto | fast | deep")
    ] = "auto",
    password: Annotated[
        str | None, typer.Option("--password", "-p", help="Password for encrypted PDFs")
    ] = None,
    extract_images: Annotated[
        bool, typer.Option("--images/--no-images", help="Extract embedded images to assets/")
    ] = True,
    include_frontmatter: Annotated[
        bool,
        typer.Option("--frontmatter/--no-frontmatter", help="Include YAML frontmatter in Markdown"),
    ] = True,
) -> None:
    """Convert a PDF document into standardized Markdown."""
    if not input_path.exists():
        console.print(f"[red]Error: Input file does not exist: {input_path}[/red]")
        raise typer.Exit(code=1)

    # Normalize conversion mode
    try:
        conv_mode = ConversionMode(mode.lower())
    except ValueError:
        console.print(f"[red]Error: Invalid mode '{mode}'. Choose auto, fast, or deep.[/red]")
        raise typer.Exit(code=1) from None

    output_dir.mkdir(parents=True, exist_ok=True)
    config = ConversionConfig(
        mode=conv_mode,
        password=password,
        extract_images=extract_images,
        output_dir=output_dir,
        include_frontmatter=include_frontmatter,
    )

    console.print(
        f"\n[bold blue]OmniPDF2MD v{__version__}[/bold blue] — Converting [cyan]{input_path.name}[/cyan]"
    )

    # 1. Pre-flight Inspection
    try:
        profiles = inspect_pdf(input_path, password=password)
    except EncryptedPDFError as err:
        console.print(f"[red]Error: {err}[/red]")
        raise typer.Exit(code=1) from None
    except Exception as err:
        console.print(f"[red]Inspection failed: {err}[/red]")
        raise typer.Exit(code=1) from None

    # Display inspection table
    table = Table(title=f"Pre-Flight Inspection ({len(profiles)} pages)", show_header=True)
    table.add_column("Page", justify="right", style="cyan")
    table.add_column("Type", style="bold")
    table.add_column("Chars", justify="right")
    table.add_column("Images", justify="right")
    table.add_column("Img Cov.", justify="right")
    table.add_column("Columns", justify="right")
    table.add_column("Table?", justify="center")
    table.add_column("Target Engine", style="green")

    for p in profiles:
        table.add_row(
            str(p.page_num),
            p.page_type.value,
            str(p.character_count),
            str(p.image_count),
            f"{p.image_area_ratio:.1%}",
            str(p.column_count),
            "Yes" if p.has_table else "No",
            p.recommended_engine,
        )
    console.print(table)

    # 2. Convert pages using SmartRouter
    def on_progress(current_page: int, total_pages: int, engine_used: str) -> None:
        console.print(
            f" -> Processed Page {current_page}/{total_pages} via [green]{engine_used}[/green]"
        )

    result = convert_pdf(input_path, config, on_progress=on_progress)

    console.print(
        Panel(
            f"[bold green]Conversion Succeeded![/bold green]\n"
            f"• Output Markdown: [cyan]{result.output_path}[/cyan]\n"
            f"• Total Pages: {result.total_pages}\n"
            f"• Engines: {', '.join(result.engines_used)}\n"
            f"• Total Duration: {result.total_time_ms:.1f}ms",
            title="Summary",
            border_style="green",
        )
    )


@app.command("doctor")
def doctor() -> None:
    """Check system health, dependencies, font availability, and local AI services."""
    console.print(f"\n[bold blue]OmniPDF2MD Doctor (v{__version__})[/bold blue]\n")

    table = Table(title="System Environment Check", show_header=True)
    table.add_column("Component", style="bold cyan")
    table.add_column("Status", style="bold")
    table.add_column("Details")

    # 1. Python Runtime
    py_ver = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
    table.add_row("Python Version", "[green]OK[/green]", f"Python {py_ver}")

    # 2. PyMuPDF
    table.add_row("PyMuPDF Engine", "[green]OK[/green]", f"fitz v{fitz.version[0]}")

    # 3. Unicode Font Check
    font_candidates = [
        Path("C:/Windows/Fonts/arial.ttf"),
        Path("C:/Windows/Fonts/segoeui.ttf"),
        Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"),
        Path("/System/Library/Fonts/Supplemental/Arial.ttf"),
    ]
    found_font = next((f for f in font_candidates if f.is_file()), None)
    if found_font:
        table.add_row("Unicode TTF Font", "[green]OK[/green]", str(found_font))
    else:
        table.add_row("Unicode TTF Font", "[yellow]Warning[/yellow]", "No Arial/DejaVu font found")

    # 4. GPU / Hardware Acceleration
    has_gpu = False
    gpu_detail = "CPU mode (Default)"
    try:
        import torch

        if torch.cuda.is_available():
            has_gpu = True
            gpu_detail = f"CUDA Available ({torch.cuda.get_device_name(0)})"
    except ImportError:
        gpu_detail = "CPU mode (Torch not installed yet - Phase 2 optional)"

    table.add_row(
        "Compute Acceleration", "[green]OK[/green]" if has_gpu else "[blue]INFO[/blue]", gpu_detail
    )

    # 5. Local Ollama Service
    ollama_status = "[red]Offline / Unreachable[/red]"
    ollama_detail = f"Cannot connect to {settings.ollama_base_url}"
    try:
        req = urllib.request.Request(
            f"{settings.ollama_base_url}/api/tags", headers={"User-Agent": "OmniPDF"}
        )
        with urllib.request.urlopen(req, timeout=1.0) as resp:
            if resp.status == 200:
                ollama_status = "[green]Online[/green]"
                ollama_detail = f"Connected to {settings.ollama_base_url}"
    except Exception as e:
        ollama_detail = (
            f"Service not running at {settings.ollama_base_url} ({e})"
        )

    table.add_row("Ollama VLM Service", ollama_status, ollama_detail)

    console.print(table)


@app.command("serve")
def serve(
    host: Annotated[
        str, typer.Option("--host", "-h", help="Host interface to bind")
    ] = "127.0.0.1",
    port: Annotated[
        int, typer.Option("--port", "-p", help="Port to listen on")
    ] = 8765,
    open_browser: Annotated[
        bool, typer.Option("--open/--no-open", help="Automatically launch default web browser")
    ] = True,
    reload: Annotated[
        bool, typer.Option("--reload", help="Enable auto-reload for development")
    ] = False,
) -> None:
    """Start the OmniPDF2MD Local Web Studio and REST API server."""
    url = f"http://{host}:{port}"
    banner = Panel.fit(
        f"[bold blue]OmniPDF2MD Studio v{__version__}[/bold blue]\n\n"
        f"• Local Web Studio:   [bold green]{url}[/bold green]\n"
        f"• API Documentation:  [cyan]{url}/docs[/cyan]\n"
        f"• OpenAPI Schema:     [cyan]{url}/openapi.json[/cyan]\n\n"
        "[dim]Press Ctrl+C to stop the server[/dim]",
        title="[bold]OmniPDF2MD Server[/bold]",
        border_style="bright_blue",
    )
    console.print(banner)

    if open_browser:
        def _launch() -> None:
            try:
                webbrowser.open_new_tab(url)
            except Exception as e:
                console.print(f"[dim]Could not open browser automatically: {e}[/dim]")

        timer = threading.Timer(1.2, _launch)
        timer.daemon = True
        timer.start()

    uvicorn.run("omnipdf.api.main:app", host=host, port=port, reload=reload, log_level="info")


if __name__ == "__main__":
    app()
