"""Extrae poblaciones del ZIP por país de https://download.geonames.org/export/dump/."""

import argparse
import csv
from pathlib import Path
from zipfile import ZipFile


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("archive", type=Path, help="ZIP XX.zip de GeoNames")
    parser.add_argument("output", type=Path, help="CSV de salida")
    parser.add_argument("--country", help="Código ISO del país, si el ZIP tiene otro nombre")
    args = parser.parse_args()
    country = (args.country or args.archive.stem).upper()
    with ZipFile(args.archive) as archive:
        lines = archive.read(f"{country}.txt").decode("utf-8").splitlines()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.writer(stream)
        writer.writerow(("name", "longitude", "latitude", "population", "geoname_id"))
        for line in lines:
            fields = line.split("\t")
            code = fields[7]
            if fields[6] != "P" or code in {"PPLCH", "PPLH", "PPLQ", "PPLW", "PPLX"}:
                continue
            writer.writerow((fields[1], fields[5], fields[4], fields[14] or "0", fields[0]))


if __name__ == "__main__":
    main()
