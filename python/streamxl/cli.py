"""PyStreamXL CLI - Spreadsheet formula extraction"""

import sys, argparse
from streamxl.cli_dashboard import PyStreamXLDashboard


def dashboard_command(args):
    try:
        dashboard = PyStreamXLDashboard(config_path=args.config)
        if args.export:
            dashboard.export_json(args.export)
        elif args.alerts:
            dashboard.show_alerts()
        elif args.recommendations:
            dashboard.show_recommendations()
        else:
            dashboard.run_dashboard(interactive=not args.static)
    except KeyboardInterrupt:
        print("\n\nDashboard stopped.")
        sys.exit(0)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(
        description="PyStreamXL - Formula Extraction & Analysis",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="Examples:\n  pystreamxl dashboard\n  pystreamxl dashboard --static\n  pystreamxl dashboard --export metrics.json"
    )

    subparsers = parser.add_subparsers(dest='command', help='Commands')

    dashboard_parser = subparsers.add_parser('dashboard', help='View extraction dashboard')
    dashboard_parser.add_argument('--static', action='store_true', help='Show static snapshot')
    dashboard_parser.add_argument('--alerts', action='store_true', help='Show alerts only')
    dashboard_parser.add_argument('--recommendations', action='store_true', help='Show recommendations')
    dashboard_parser.add_argument('--export', metavar='FILE', help='Export to JSON')
    dashboard_parser.add_argument('--config', metavar='PATH', help='Config file path')
    dashboard_parser.set_defaults(func=dashboard_command)

    parser.add_argument('--version', action='version', version='PyStreamXL 5.1.0')

    args = parser.parse_args()

    if args.command is None:
        parser.print_help()
        sys.exit(0)

    if hasattr(args, 'func'):
        args.func(args)


if __name__ == '__main__':
    main()
