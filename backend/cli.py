import asyncio
import click
import json
import httpx
from rich.console import Console
from rich.table import Table

console = Console()
API_BASE_URL = "http://localhost:8000/api/v1"

@click.group()
def cli():
    """Lead Intelligence Platform CLI Tool"""
    pass

@cli.command()
def init():
    """Initialize the platform database and directories"""
    console.print("[bold blue]Initializing Lead Intelligence Platform...[/bold blue]")
    
    # Initialize DB (local script)
    from platform_app.database.init_db import init_database
    try:
        init_database()
        console.print("[green]✓ Database schema created successfully[/green]")
    except Exception as e:
        console.print(f"[red]Error initializing database: {str(e)}[/red]")

@cli.group()
def company():
    """Manage companies"""
    pass

@company.command("create")
@click.option("--name", required=True, help="Company name")
@click.option("--website", help="Company website")
@click.option("--desc", help="Company description")
def company_create(name, website, desc):
    """Create a new company"""
    with httpx.Client() as client:
        try:
            response = client.post(
                f"{API_BASE_URL}/companies",
                json={"name": name, "website": website, "description": desc}
            )
            if response.status_code == 201:
                data = response.json()
                console.print(f"[green]✓ Company '{name}' created with ID: {data['id']}[/green]")
            else:
                console.print(f"[red]Error: {response.text}[/red]")
        except httpx.RequestError as e:
            console.print(f"[red]Connection Error: Is the API running? ({str(e)})[/red]")

@cli.group()
def product():
    """Manage products"""
    pass

@product.command("create")
@click.option("--company-id", required=True, help="Company ID")
@click.option("--name", required=True, help="Product name")
@click.option("--desc", help="Product description")
def product_create(company_id, name, desc):
    """Create a new product"""
    with httpx.Client() as client:
        try:
            response = client.post(
                f"{API_BASE_URL}/products",
                json={"company_id": company_id, "name": name, "description": desc}
            )
            if response.status_code == 201:
                data = response.json()
                console.print(f"[green]✓ Product '{name}' created with ID: {data['id']}[/green]")
            else:
                console.print(f"[red]Error: {response.text}[/red]")
        except httpx.RequestError as e:
            console.print(f"[red]Connection Error: Is the API running? ({str(e)})[/red]")

@cli.group()
def knowledge():
    """Manage knowledge library"""
    pass

@knowledge.command("list")
@click.option("--company-id", required=True, help="Company ID")
def knowledge_list(company_id):
    """List knowledge documents"""
    with httpx.Client() as client:
        try:
            response = client.get(f"{API_BASE_URL}/knowledge/company/{company_id}")
            if response.status_code == 200:
                docs = response.json()
                if not docs:
                    console.print("[yellow]No documents found.[/yellow]")
                    return
                
                table = Table(title=f"Knowledge Documents (Company: {company_id})")
                table.add_column("ID", style="cyan")
                table.add_column("Filename", style="magenta")
                table.add_column("Status", style="green")
                table.add_column("Size (KB)")
                
                for doc in docs:
                    table.add_row(
                        doc['id'], 
                        doc['original_filename'], 
                        doc['status'], 
                        f"{doc['file_size'] / 1024:.1f}"
                    )
                
                console.print(table)
            else:
                console.print(f"[red]Error: {response.text}[/red]")
        except httpx.RequestError as e:
            console.print(f"[red]Connection Error: Is the API running? ({str(e)})[/red]")

@knowledge.command("upload")
@click.argument("file_path", type=click.Path(exists=True))
@click.option("--company-id", required=True, help="Company ID")
def knowledge_upload(file_path, company_id):
    """Upload a knowledge document"""
    with httpx.Client() as client:
        try:
            import os
            with open(file_path, "rb") as f:
                files = {"file": (os.path.basename(file_path), f)}
                data = {"company_id": company_id}
                
                console.print(f"[blue]Uploading {file_path}...[/blue]")
                response = client.post(f"{API_BASE_URL}/knowledge/upload", files=files, data=data)
                
                if response.status_code == 200:
                    console.print("[green]✓ Document uploaded successfully[/green]")
                else:
                    console.print(f"[red]Error: {response.text}[/red]")
        except httpx.RequestError as e:
            console.print(f"[red]Connection Error: Is the API running? ({str(e)})[/red]")

@cli.group()
def lead():
    """Phase 2: Manage leads and search discovery"""
    pass

@lead.command("search")
@click.option("--company-id", required=True, help="Your Company ID")
@click.option("--workspace-id", required=True, help="Workspace ID")
@click.option("--keywords", help="Comma-separated keywords")
def lead_search(company_id, workspace_id, keywords):
    """Trigger AI lead discovery"""
    kw_list = [k.strip() for k in keywords.split(",")] if keywords else []
    with httpx.Client() as client:
        try:
            console.print(f"[blue]Starting Lead Discovery for {company_id}...[/blue]")
            response = client.post(
                f"{API_BASE_URL}/search/discover",
                params={"workspace_id": workspace_id},
                json={"company_id": company_id, "custom_keywords": kw_list}
            )
            if response.status_code == 200:
                data = response.json()
                console.print(f"[green]✓ {data.get('message', 'Discovery started in background')}[/green]")
                console.print("Watch the dashboard for realtime updates.")
            else:
                console.print(f"[red]Error: {response.text}[/red]")
        except httpx.RequestError as e:
            console.print(f"[red]Connection Error: Is the API running? ({str(e)})[/red]")

@lead.command("status")
@click.option("--workspace-id", required=True, help="Workspace ID")
def lead_status(workspace_id):
    """View lead discovery dashboard stats"""
    with httpx.Client() as client:
        try:
            response = client.get(f"{API_BASE_URL}/leads/dashboard", params={"workspace_id": workspace_id})
            if response.status_code == 200:
                stats = response.json()
                console.print("\n[bold cyan]Lead Discovery Dashboard[/bold cyan]")
                console.print(f"Total Leads Discovered: [bold]{stats['total_leads']}[/bold]")
                
                table = Table(title="By Quality Tier")
                table.add_column("Tier", style="magenta")
                table.add_column("Count", style="green")
                table.add_row("High", str(stats.get('high_quality_leads', 0)))
                table.add_row("Medium", str(stats.get('medium_leads', 0)))
                table.add_row("Low", str(stats.get('low_leads', 0)))
                console.print(table)
            else:
                console.print(f"[red]Error: {response.text}[/red]")
        except httpx.RequestError as e:
            console.print(f"[red]Connection Error: Is the API running? ({str(e)})[/red]")


@cli.command()
def status():
    """Check platform health status"""
    with httpx.Client() as client:
        try:
            response = client.get(f"{API_BASE_URL}/health")
            if response.status_code == 200:
                data = response.json()
                console.print("[bold]System Health Status:[/bold]")
                for k, v in data.items():
                    color = "green" if v == "ok" else "yellow" if v != "error" else "red"
                    console.print(f"- {k}: [{color}]{v}[/{color}]")
            else:
                console.print(f"[red]Error: {response.text}[/red]")
        except httpx.RequestError as e:
            console.print(f"[red]Backend is offline or unreachable ({str(e)})[/red]")

if __name__ == "__main__":
    cli()
