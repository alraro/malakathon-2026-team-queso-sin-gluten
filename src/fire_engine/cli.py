import argparse
import json
from pathlib import Path

from fire_engine import AlertDistances, Georeference, analyse_scene, load_composite
from fire_engine.validation import render_report, validate_data


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    if args.command == "validate":
        return _validate(args)
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
    analyse.add_argument("--settlements", type=Path, help="CSV de poblaciones (por defecto, GeoNames España)")
    analyse.add_argument("--high-fire-km", type=float, default=2.0, help="Alerta alta por cercanía a un foco")
    analyse.add_argument("--medium-km", type=float, default=5.0, help="Umbral de alerta media")
    analyse.add_argument("--watch-km", type=float, default=10.0, help="Umbral de vigilancia")
    validate = commands.add_parser(
        "validate", help="Informe de métricas de autoconsistencia sobre las escenas de data/"
    )
    validate.add_argument(
        "--data", type=Path, default=Path("data"), help="Directorio con una carpeta por escena"
    )
    validate.add_argument("--out", type=Path, help="Fichero Markdown donde guardar el informe")
    return parser


def _validate(args: argparse.Namespace) -> int:
    report = render_report(validate_data(args.data))
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(report, encoding="utf-8")
    print(report, end="")
    return 0


def _analyse(args: argparse.Namespace) -> int:
    args.out.mkdir(parents=True, exist_ok=True)
    result = analyse_scene(
        load_composite(args.swir),
        true_color=load_composite(args.true_color) if args.true_color else None,
        wildfires=load_composite(args.wildfires) if args.wildfires else None,
        georeference=Georeference(tuple(args.bbox), "manual") if args.bbox else None,
        out_dir=args.out,
        settlements_path=args.settlements,
        alert_distances=AlertDistances(args.high_fire_km, args.medium_km, args.watch_km),
    )
    output = args.out / "result.json"
    output.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
    print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
