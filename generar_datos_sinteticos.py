#!/usr/bin/env python3
"""Genera un dataset ficticio para demostrar el flujo analítico."""

from __future__ import annotations

import argparse
import csv
import random
from datetime import date, timedelta
from pathlib import Path


HEADERS = [
    "Tipo",
    "Clave",
    "Número de Documento",
    "Código Cliente",
    "Folio",
    "Fecha de Documento",
    "Último día mes Documento",
    "Fecha de Vencimiento",
    "Monto Documento",
    "Número de Pago_SAP",
    "Fecha de Pago",
    "Monto Pago",
    "Número de Pago",
    "Importe Acumulado de Pagos",
    "Importe Acumulado al Saldo",
]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default="data/historico_sintetico.csv")
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    random.seed(args.seed)
    cutoff = date(2026, 6, 20)
    rows = []
    document_number = 10000

    for client_index in range(1, 41):
        client = f"C{client_index:03d}"
        first_purchase = cutoff - timedelta(days=random.randint(90, 2400))
        is_high_value = client_index <= 8

        for month_offset in range(0, 12):
            purchase_date = first_purchase + timedelta(days=month_offset * 30 + random.randint(0, 8))
            if purchase_date >= cutoff:
                break
            amount = random.randint(8000, 25000) if is_high_value else random.randint(800, 7000)
            due_date = purchase_date + timedelta(days=30)
            overdue = random.random() < (0.24 if is_high_value else 0.10)
            payment_date = due_date + timedelta(days=random.randint(35, 90)) if overdue else due_date + timedelta(days=random.randint(-5, 20))
            open_balance = amount if overdue and random.random() < 0.55 else 0

            rows.append(
                [
                    "Factura",
                    "VENTA",
                    f"F{document_number}",
                    client,
                    f"FOL-{document_number}",
                    purchase_date.isoformat(),
                    purchase_date.replace(day=28).isoformat(),
                    due_date.isoformat(),
                    amount,
                    f"P{document_number}",
                    "" if open_balance else payment_date.isoformat(),
                    0 if open_balance else amount,
                    f"P{document_number}",
                    0 if open_balance else amount,
                    open_balance,
                ]
            )
            document_number += 1

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.writer(stream)
        writer.writerow(HEADERS)
        writer.writerows(rows)
    print(f"OK -> {output.resolve()} ({len(rows)} documentos sintéticos)")


if __name__ == "__main__":
    main()
