"""Tests for the CLI argument parser (pure Python)."""
from nommo_slicer.cli.main import build_parser


class TestCLI:
    def test_parser_accepts_slice_command(self):
        parser = build_parser()
        args = parser.parse_args(["slice", "input.3mf", "--output", "output.3mf"])
        assert args.command == "slice"
        assert str(args.input_3mf) == "input.3mf"
        assert str(args.output) == "output.3mf"

    def test_parser_defaults(self):
        parser = build_parser()
        args = parser.parse_args(["slice", "in.3mf", "-o", "out.3mf"])
        assert args.plate is None
        assert args.threads is None
        assert args.replace_existing_metadata is False
        assert args.json is False

    def test_parser_all_flags(self):
        parser = build_parser()
        args = parser.parse_args([
            "slice", "in.3mf", "-o", "out.3mf",
            "--profiles-dir", "./profiles",
            "--printer-profile", "X1C",
            "--process-profile", "0.20mm Standard",
            "--filament-profile", "PLA Basic",
            "--plate", "1",
            "--threads", "4",
            "--temp-dir", "/tmp/foo",
            "--replace-existing-metadata",
            "--json",
        ])
        assert args.printer_profile == "X1C"
        assert args.plate == 1
        assert args.threads == 4
        assert args.replace_existing_metadata is True
        assert args.json is True
