"""PyStreamXL CLI Dashboard - Formula extraction monitoring"""

import sys, platform
from datetime import datetime
from typing import Optional, Dict, Any
from dataclasses import dataclass


@dataclass
class DashboardMetrics:
    timestamp: str
    title: str
    metrics: Dict[str, Any]
    alerts: list
    recommendations: list


def get_dashboard_impl(product_name: str):
    platform_name = platform.system()
    if platform_name == "Darwin":
        try:
            from rich.console import Console
            return RichDashboard(product_name)
        except ImportError:
            return SimpleDashboard(product_name)
    elif platform_name == "Linux":
        try:
            from textual.app import App
            return TextualDashboard(product_name)
        except ImportError:
            try:
                from rich.console import Console
                return RichDashboard(product_name)
            except ImportError:
                return SimpleDashboard(product_name)
    else:
        try:
            from rich.console import Console
            return RichDashboard(product_name)
        except ImportError:
            return SimpleDashboard(product_name)


class SimpleDashboard:
    def __init__(self, product_name: str):
        self.product_name = product_name

    def render(self, data: DashboardMetrics) -> None:
        print(f"\n{'='*80}\n✓ {data.title}\n  {data.timestamp}\n{'='*80}\n")
        print("KEY METRICS:")
        for key, value in data.metrics.items():
            if isinstance(value, dict):
                print(f"  {key}:")
                for k, v in value.items():
                    print(f"    {k}: {v}")
            else:
                print(f"  {key}: {value}")
        if data.alerts:
            print("\n⚠️  ALERTS:")
            for alert in data.alerts:
                print(f"  [{alert.get('level', '').upper()}] {alert.get('message', '')}")
        if data.recommendations:
            print("\n💡 RECOMMENDATIONS:")
            for rec in data.recommendations:
                print(f"  [{rec.get('type', '').upper()}] {rec.get('message', '')}")
        print(f"\n{'='*80}\n")

    def run(self) -> None:
        self.render(DashboardMetrics(datetime.now().isoformat(), f"{self.product_name} Dashboard", {"Status": "Active"}, [], []))


class RichDashboard:
    def __init__(self, product_name: str):
        self.product_name = product_name
        try:
            from rich.console import Console
            self.console = Console()
        except ImportError:
            print("Error: Rich required. Install with: pip install rich")
            sys.exit(1)

    def render(self, data: DashboardMetrics) -> None:
        from rich.table import Table
        self.console.print(f"\n[bold cyan]{'='*80}[/bold cyan]")
        self.console.print(f"[bold cyan]✓ {data.title}[/bold cyan]")
        self.console.print(f"[dim cyan]{data.timestamp}[/dim cyan]")
        self.console.print(f"[bold cyan]{'='*80}[/bold cyan]\n")

        table = Table(title="[bold]Key Metrics[/bold]")
        table.add_column("Metric", style="cyan")
        table.add_column("Value", style="green")
        for key, value in data.metrics.items():
            if isinstance(value, dict):
                for k, v in value.items():
                    table.add_row(f"  {key} → {k}", str(v))
            else:
                table.add_row(key, str(value))
        self.console.print(table)

        if data.alerts:
            self.console.print("\n[bold red]⚠️  ALERTS[/bold red]")
            for alert in data.alerts:
                self.console.print(f"  [{alert.get('level', 'info').upper()}] {alert.get('message', '')}")
        if data.recommendations:
            self.console.print("\n[bold yellow]💡 RECOMMENDATIONS[/bold yellow]")
            for rec in data.recommendations:
                self.console.print(f"  [{rec.get('type', '').upper()}] {rec.get('message', '')}")
        self.console.print(f"\n[bold cyan]{'='*80}[/bold cyan]\n")

    def run(self) -> None:
        self.render(DashboardMetrics(datetime.now().isoformat(), f"{self.product_name} Dashboard", {"Status": "Active"}, [], []))


class TextualDashboard:
    def __init__(self, product_name: str):
        self.product_name = product_name
        self.has_textual = False
        try:
            from textual.app import App
            self.has_textual = True
        except ImportError:
            pass

    def render(self, data: DashboardMetrics) -> None:
        if not self.has_textual:
            RichDashboard(self.product_name).render(data)
            return
        RichDashboard(self.product_name).render(data)

    def run(self) -> None:
        if not self.has_textual:
            RichDashboard(self.product_name).run()
            return
        self.render(DashboardMetrics(datetime.now().isoformat(), f"{self.product_name} Dashboard", {"Status": "Active"}, [], []))


class PyStreamXLDashboard:
    def __init__(self, config_path: Optional[str] = None):
        self.config_path = config_path or "./pystreamxl.yaml"
        self.dashboard = get_dashboard_impl("PyStreamXL v1.2.0")

    def get_mock_metrics(self) -> DashboardMetrics:
        return DashboardMetrics(
            datetime.now().isoformat(),
            "PyStreamXL Formula Extraction Dashboard",
            {
                "Status": "🟢 Processing",
                "Uptime": "7 days 2h 30m",
                "Processing": {
                    "Pending": "23 files (45 MB)",
                    "Processing": "2 files",
                    "Completed": "567 files",
                    "Failed": "3 files",
                },
                "Formulas Extracted": {
                    "Total": "45,234",
                    "Simple": "32,451 (71.8%)",
                    "Complex": "12,783 (28.2%)",
                    "Broken Refs": "234 (0.5%)",
                },
                "Quality": {
                    "Avg Complexity": "2.3",
                    "Max Depth": "7",
                    "Circular Refs": "0",
                },
                "Performance": {
                    "Speed": "12.3 files/min",
                    "Rate": "1,247 formulas/min",
                    "Avg Time": "4.9s per file",
                },
            },
            [
                {"level": "info", "message": "Formula extraction running smoothly"},
                {"level": "warning", "message": "3 files failed to parse (complex formulas)"},
            ],
            [
                {"type": "performance", "message": "Consider GPU acceleration for complex formulas"},
                {"type": "quality", "message": "234 broken references detected - review mapping"},
            ]
        )

    def run_dashboard(self, interactive: bool = True) -> None:
        try:
            metrics = self.get_mock_metrics()
            if interactive:
                self.dashboard.run()
            else:
                self.dashboard.render(metrics)
        except KeyboardInterrupt:
            print("\n\nDashboard stopped.")
            sys.exit(0)
        except Exception as e:
            print(f"Error: {e}", file=sys.stderr)
            sys.exit(1)

    def show_alerts(self) -> None:
        metrics = self.get_mock_metrics()
        print("\n[ALERTS]")
        if metrics.alerts:
            for alert in metrics.alerts:
                print(f"  [{alert['level'].upper()}] {alert['message']}")

    def show_recommendations(self) -> None:
        metrics = self.get_mock_metrics()
        print("\n[RECOMMENDATIONS]")
        if metrics.recommendations:
            for rec in metrics.recommendations:
                print(f"  [{rec['type'].upper()}] {rec['message']}")

    def export_json(self, output_file: str) -> None:
        import json
        metrics = self.get_mock_metrics()
        data = {
            "timestamp": metrics.timestamp,
            "title": metrics.title,
            "metrics": metrics.metrics,
            "alerts": metrics.alerts,
            "recommendations": metrics.recommendations,
        }
        with open(output_file, 'w') as f:
            json.dump(data, f, indent=2)
        print(f"✓ Metrics exported to {output_file}")
