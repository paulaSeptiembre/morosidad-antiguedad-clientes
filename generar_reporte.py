#!/usr/bin/env python3
"""Genera un reporte markdown a partir de las salidas del analisis."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def table_md(rows, columns):
    header = "| " + " | ".join(columns) + " |"
    sep = "| " + " | ".join(["---"] * len(columns)) + " |"
    lines = [header, sep]
    for r in rows:
        lines.append("| " + " | ".join(str(r.get(c, "")) for c in columns) + " |")
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--outdir", default="output")
    parser.add_argument("--report", default="output/reporte_resultados.md")
    args = parser.parse_args()

    outdir = Path(args.outdir)
    resumen = json.loads((outdir / "resumen_metricas.json").read_text(encoding="utf-8"))
    tablas = json.loads((outdir / "tablas_resumen.json").read_text(encoding="utf-8"))

    m = resumen["metadata"]
    q1 = resumen["q1_relacion_antiguedad_morosidad"]

    lines = []
    lines.append("# Reporte de morosidad por antiguedad y volumen de compra")
    lines.append("")
    lines.append("## Metadatos")
    lines.append(f"- Fecha de corte: {m['fecha_corte']}")
    lines.append(f"- Documentos analizados: {m['n_documentos']}")
    lines.append(f"- Clientes analizados: {m['n_clientes']}")
    lines.append(f"- Clientes en Pareto 80/20: {m['n_clientes_pareto_80']}")
    lines.append(f"- Umbral de mora (dias): {m['umbral_mora_dias']}")
    lines.append("")

    lines.append("## 1) Relacion entre antiguedad y morosidad")
    lines.append(f"- Correlacion point-biserial: {q1['correlacion_point_biserial']}")
    lines.append(f"- p-value (permutacion): {q1['p_value_permutacion']}")
    lines.append(f"- Significativa (alpha=0.05): {q1['significativa_alpha_005']}")
    lines.append("")

    lines.append("## 2) Riesgo por rangos de antiguedad")
    lines.append(
        table_md(
            tablas["q2_riesgo_por_segmento"],
            ["segmento", "n_documentos", "n_incumplimiento", "riesgo_incumplimiento", "ingreso_estancado"],
        )
    )
    lines.append("")

    lines.append("## 3) Perfil de morosidad en clientes activos con compras mensuales")
    lines.append(
        table_md(
            tablas["q3_clientes_activos_compras_mensuales"],
            ["segmento", "n_documentos", "riesgo_incumplimiento", "ingreso_estancado"],
        )
    )
    lines.append("")

    lines.append("## 4) Segmento con mayor ingreso estancado")
    q4 = sorted(tablas["q4_ingreso_estancado_por_segmento"], key=lambda x: x["ingreso_estancado"], reverse=True)
    top = q4[0] if q4 else {"segmento": "N/A", "ingreso_estancado": 0}
    lines.append(f"- Segmento lider: {top['segmento']}")
    lines.append(f"- Ingreso estancado: {top['ingreso_estancado']}")
    lines.append("")

    lines.append("## 5) Interaccion antiguedad x volumen de compra (Pareto 80/20)")
    lines.append(
        table_md(
            tablas["q5_interaccion_antiguedad_pareto"],
            ["segmento", "grupo_volumen", "n_documentos", "prob_incumplimiento"],
        )
    )
    lines.append("")

    Path(args.report).write_text("\n".join(lines), encoding="utf-8")
    print(f"OK -> reporte: {Path(args.report).resolve()}")


if __name__ == "__main__":
    main()