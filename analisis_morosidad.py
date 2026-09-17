#!/usr/bin/env python3
"""Analisis de morosidad por antiguedad y volumen de compra.

Este script trabaja con librerias estandar (sin pandas) y genera:
- output/documentos_enriquecidos.csv
- output/resumen_metricas.json
- output/tablas_resumen.json
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import random
import unicodedata
from collections import defaultdict
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple

DATE_FMT = "%Y-%m-%d"


@dataclass
class DocRecord:
    doc_id: str
    cliente: str
    fecha_doc: Optional[date]
    fecha_venc: Optional[date]
    monto_doc: float
    fecha_ultimo_pago: Optional[date]
    saldo_actual: float


def normalize(text: str) -> str:
    base = "".join(ch for ch in unicodedata.normalize("NFKD", text) if not unicodedata.combining(ch))
    return base.lower().strip()


def parse_date(raw: str) -> Optional[date]:
    value = (raw or "").strip()
    if not value:
        return None
    try:
        return datetime.strptime(value, DATE_FMT).date()
    except ValueError:
        return None


def parse_float(raw: str) -> float:
    value = (raw or "").strip().replace(",", "")
    if not value:
        return 0.0
    try:
        return float(value)
    except ValueError:
        return 0.0


def find_col(col_map: Dict[str, str], needle: str) -> str:
    for key, original in col_map.items():
        if needle in key:
            return original
    raise KeyError(f"No se encontro columna para patron: {needle}")


def load_docs(csv_path: Path) -> Dict[str, DocRecord]:
    docs: Dict[str, DocRecord] = {}

    with csv_path.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        if not reader.fieldnames:
            raise ValueError("CSV sin cabeceras")
        cmap = {normalize(c): c for c in reader.fieldnames}

        c_doc = find_col(cmap, "numero de documento")
        c_cliente = find_col(cmap, "codigo cliente")
        c_fdoc = find_col(cmap, "fecha de documento")
        c_fvenc = find_col(cmap, "fecha de vencimiento")
        c_monto = find_col(cmap, "monto documento")
        c_fpago = find_col(cmap, "fecha de pago")
        c_saldo = find_col(cmap, "acumulado al saldo")

        for row in reader:
            doc_id = row[c_doc]
            cliente = row[c_cliente]
            fecha_doc = parse_date(row[c_fdoc])
            fecha_venc = parse_date(row[c_fvenc])
            monto_doc = parse_float(row[c_monto])
            fecha_pago = parse_date(row[c_fpago])
            saldo = parse_float(row[c_saldo])

            current = docs.get(doc_id)
            if current is None:
                docs[doc_id] = DocRecord(
                    doc_id=doc_id,
                    cliente=cliente,
                    fecha_doc=fecha_doc,
                    fecha_venc=fecha_venc,
                    monto_doc=monto_doc,
                    fecha_ultimo_pago=fecha_pago,
                    saldo_actual=saldo,
                )
                continue

            if current.fecha_doc is None or (fecha_doc and fecha_doc < current.fecha_doc):
                current.fecha_doc = fecha_doc
            if current.fecha_venc is None or (fecha_venc and fecha_venc < current.fecha_venc):
                current.fecha_venc = fecha_venc
            if fecha_pago and (current.fecha_ultimo_pago is None or fecha_pago > current.fecha_ultimo_pago):
                current.fecha_ultimo_pago = fecha_pago
            # En el historico, el saldo acumulado suele quedar actualizado en la ultima fila del doc.
            current.saldo_actual = saldo

    return docs


def edad_segment(antig_dias: int) -> str:
    if antig_dias < 183:
        return "< 6 meses"
    if antig_dias < 365:
        return "6-12 meses (~1 anio)"
    if antig_dias < 365 * 3:
        return "1-3 anios"
    if antig_dias < 365 * 5:
        return "3-5 anios"
    return "> 5 anios"


def corr_point_biserial(xs: List[float], ys: List[int]) -> float:
    n = len(xs)
    if n < 2:
        return 0.0
    mx = sum(xs) / n
    my = sum(ys) / n
    cov = sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / (n - 1)
    vx = sum((x - mx) ** 2 for x in xs) / (n - 1)
    vy = sum((y - my) ** 2 for y in ys) / (n - 1)
    if vx <= 0 or vy <= 0:
        return 0.0
    return cov / math.sqrt(vx * vy)


def permutation_pvalue(xs: List[float], ys: List[int], observed: float, n_perm: int, seed: int) -> float:
    random.seed(seed)
    abs_obs = abs(observed)
    hits = 0
    shuffled = ys[:]
    for _ in range(n_perm):
        random.shuffle(shuffled)
        r = corr_point_biserial(xs, shuffled)
        if abs(r) >= abs_obs:
            hits += 1
    # correccion de continuidad
    return (hits + 1) / (n_perm + 1)


def month_key(d: date) -> Tuple[int, int]:
    return d.year, d.month


def previous_months(anchor: date, n: int) -> List[Tuple[int, int]]:
    out = []
    y, m = anchor.year, anchor.month
    for _ in range(n):
        out.append((y, m))
        m -= 1
        if m == 0:
            m = 12
            y -= 1
    return out


def main() -> None:
    parser = argparse.ArgumentParser(description="Analisis de morosidad desde historico.csv")
    parser.add_argument("--input", default="historico.csv", help="Ruta al CSV fuente")
    parser.add_argument("--outdir", default="output", help="Directorio de salida")
    parser.add_argument("--fecha-corte", default=str(date.today()), help="Fecha corte YYYY-MM-DD")
    parser.add_argument("--mora-dias", type=int, default=30, help="Umbral de mora en dias")
    parser.add_argument("--perm", type=int, default=1000, help="Permutaciones para p-value")
    args = parser.parse_args()

    fecha_corte = datetime.strptime(args.fecha_corte, DATE_FMT).date()
    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)

    docs_map = load_docs(Path(args.input))
    docs = list(docs_map.values())

    first_doc_by_client: Dict[str, date] = {}
    buy_by_client: Dict[str, float] = defaultdict(float)
    months_by_client: Dict[str, set] = defaultdict(set)

    for d in docs:
        if d.fecha_doc:
            first = first_doc_by_client.get(d.cliente)
            if first is None or d.fecha_doc < first:
                first_doc_by_client[d.cliente] = d.fecha_doc
            months_by_client[d.cliente].add(month_key(d.fecha_doc))
        buy_by_client[d.cliente] += d.monto_doc

    # Pareto 80/20 por cliente segun monto total comprado
    total_buy = sum(buy_by_client.values())
    ranked = sorted(buy_by_client.items(), key=lambda kv: kv[1], reverse=True)
    pareto_clients = set()
    accum = 0.0
    for client, amount in ranked:
        if total_buy <= 0:
            break
        accum += amount
        pareto_clients.add(client)
        if accum / total_buy >= 0.80:
            break

    target_months = set(previous_months(fecha_corte, 6))

    enriched_rows = []
    xs_age: List[float] = []
    ys_default: List[int] = []

    by_segment = defaultdict(lambda: {"n": 0, "inc": 0, "ingreso_estancado": 0.0})
    by_seg_pareto = defaultdict(lambda: {"n": 0, "inc": 0})
    active_monthly_profile = defaultdict(lambda: {"n": 0, "inc": 0, "saldo": 0.0})

    for d in docs:
        if not d.fecha_doc:
            continue

        first_date = first_doc_by_client.get(d.cliente, d.fecha_doc)
        antig_dias = max((d.fecha_doc - first_date).days, 0)
        segment = edad_segment(antig_dias)

        dias_atraso = 0
        if d.fecha_venc:
            if d.saldo_actual > 0:
                dias_atraso = (fecha_corte - d.fecha_venc).days
            elif d.fecha_ultimo_pago:
                dias_atraso = (d.fecha_ultimo_pago - d.fecha_venc).days

        incumplimiento = 1 if dias_atraso > args.mora_dias else 0
        ingreso_estancado = d.saldo_actual if d.saldo_actual > 0 else 0.0
        is_pareto = d.cliente in pareto_clients
        is_active_monthly = target_months.issubset(months_by_client.get(d.cliente, set()))

        row = {
            "doc_id": d.doc_id,
            "cliente": d.cliente,
            "fecha_doc": d.fecha_doc.isoformat(),
            "fecha_venc": d.fecha_venc.isoformat() if d.fecha_venc else "",
            "fecha_ultimo_pago": d.fecha_ultimo_pago.isoformat() if d.fecha_ultimo_pago else "",
            "monto_doc": round(d.monto_doc, 2),
            "saldo_actual": round(d.saldo_actual, 2),
            "antiguedad_cliente_dias": antig_dias,
            "segmento_antiguedad": segment,
            "dias_atraso": dias_atraso,
            "incumplimiento": incumplimiento,
            "cliente_pareto_80": 1 if is_pareto else 0,
            "cliente_activo_compras_mensuales": 1 if is_active_monthly else 0,
        }
        enriched_rows.append(row)

        xs_age.append(float(antig_dias))
        ys_default.append(incumplimiento)

        g = by_segment[segment]
        g["n"] += 1
        g["inc"] += incumplimiento
        g["ingreso_estancado"] += ingreso_estancado

        gp = by_seg_pareto[(segment, "pareto" if is_pareto else "no_pareto")]
        gp["n"] += 1
        gp["inc"] += incumplimiento

        if is_active_monthly:
            ga = active_monthly_profile[segment]
            ga["n"] += 1
            ga["inc"] += incumplimiento
            ga["saldo"] += ingreso_estancado

    # Q1: relacion estadistica entre antiguedad e incumplimiento
    corr = corr_point_biserial(xs_age, ys_default)
    p_value = permutation_pvalue(xs_age, ys_default, corr, n_perm=args.perm, seed=42)

    # Estructuras serializables
    segment_table = []
    for seg, vals in sorted(by_segment.items()):
        n = vals["n"]
        inc = vals["inc"]
        segment_table.append(
            {
                "segmento": seg,
                "n_documentos": n,
                "n_incumplimiento": inc,
                "riesgo_incumplimiento": round(inc / n, 4) if n else 0.0,
                "ingreso_estancado": round(vals["ingreso_estancado"], 2),
            }
        )

    interaction_table = []
    for (seg, grp), vals in sorted(by_seg_pareto.items()):
        n = vals["n"]
        inc = vals["inc"]
        interaction_table.append(
            {
                "segmento": seg,
                "grupo_volumen": grp,
                "n_documentos": n,
                "prob_incumplimiento": round(inc / n, 4) if n else 0.0,
            }
        )

    active_table = []
    for seg, vals in sorted(active_monthly_profile.items()):
        n = vals["n"]
        inc = vals["inc"]
        active_table.append(
            {
                "segmento": seg,
                "n_documentos": n,
                "riesgo_incumplimiento": round(inc / n, 4) if n else 0.0,
                "ingreso_estancado": round(vals["saldo"], 2),
            }
        )

    resumen = {
        "metadata": {
            "input": args.input,
            "fecha_corte": fecha_corte.isoformat(),
            "umbral_mora_dias": args.mora_dias,
            "n_documentos": len(enriched_rows),
            "n_clientes": len(first_doc_by_client),
            "n_clientes_pareto_80": len(pareto_clients),
            "perm_test_n": args.perm,
        },
        "q1_relacion_antiguedad_morosidad": {
            "correlacion_point_biserial": round(corr, 6),
            "p_value_permutacion": round(p_value, 6),
            "significativa_alpha_005": p_value < 0.05,
        },
    }

    with (outdir / "documentos_enriquecidos.csv").open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(enriched_rows[0].keys()))
        writer.writeheader()
        writer.writerows(enriched_rows)

    with (outdir / "resumen_metricas.json").open("w", encoding="utf-8") as f:
        json.dump(resumen, f, ensure_ascii=False, indent=2)

    with (outdir / "tablas_resumen.json").open("w", encoding="utf-8") as f:
        json.dump(
            {
                "q2_riesgo_por_segmento": segment_table,
                "q3_clientes_activos_compras_mensuales": active_table,
                "q4_ingreso_estancado_por_segmento": [
                    {"segmento": r["segmento"], "ingreso_estancado": r["ingreso_estancado"]} for r in segment_table
                ],
                "q5_interaccion_antiguedad_pareto": interaction_table,
            },
            f,
            ensure_ascii=False,
            indent=2,
        )

    print(f"OK -> salidas en: {outdir.resolve()}")


if __name__ == "__main__":
    main()