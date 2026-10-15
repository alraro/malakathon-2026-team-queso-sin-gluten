import argparse
import json
from pathlib import Path

from fire_engine import Georeference, analyse_scene, load_composite


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    return _analyse(args)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="fire-engine")
    commands = parser.add_subparsers(dest="command", required=True)
    analyse = commands.add_parser("analyse", help="Analiza una escena y escribe result.json")
    analyse.add_argument("--swir", required=True, type=Path, help="Composición SWIR (obligatoria)")
    analyse.add_argument("--true-color", type=Path, help="Composición True Color")
    analyse.add_argument("--wildfires", type=Path, help="Composición Wildfires")
    analyse.add_argument(
        "--bbox",
        nargs=4,
        type=float,
        metavar=("LON_MIN", "LAT_MIN", "LON_MAX", "LAT_MAX"),
        help="Georreferencia de la escena en grados WGS84",
    )
    analyse.add_argument("--out", required=True, type=Path, help="Directorio de salida")
    return parser


def _analyse(args: argparse.Namespace) -> int:
    args.out.mkdir(parents=True, exist_ok=True)
    result = analyse_scene(
        load_composite(args.swir),
        true_color=load_composite(args.true_color) if args.true_color else None,
        wildfires=load_composite(args.wildfires) if args.wildfires else None,
        georeference=Georeference(tuple(args.bbox), "manual") if args.bbox else None,
        output_dir=args.out,
    )
    output = args.out / "result.json"
    output.write_text(json.dumps(result, indent=2, ensure_ascii=False))
    print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
