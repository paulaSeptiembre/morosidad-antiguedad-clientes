# Morosidad y antigüedad de clientes

Proyecto académico de la Maestría en Ciencia de Datos para Negocios. Examina la relación entre antigüedad de clientes, actividad de compra, concentración de ventas y riesgo de morosidad para apoyar la priorización de cartera.

## Problema de negocio

Los equipos de crédito y cobranza necesitan decidir qué segmentos requieren seguimiento prioritario. Este análisis segmenta los documentos por antigüedad del cliente, comportamiento de compra y clasificación Pareto 80/20 para encontrar señales accionables sin asumir que una correlación demuestra causalidad.

## Preguntas de análisis

1. ¿Existe una asociación estadística entre antigüedad y morosidad?
2. ¿Cómo cambia el riesgo de incumplimiento por rango de antigüedad?
3. ¿Qué perfil presentan los clientes con compras mensuales activas?
4. ¿En qué segmento se concentra el saldo pendiente?
5. ¿Cómo cambia el riesgo al combinar antigüedad y volumen de compra Pareto 80/20?

## Enfoque

El flujo procesa un archivo CSV a nivel documento y:

- deriva antigüedad, días de atraso, actividad mensual y pertenencia a Pareto;
- define morosidad como atraso mayor a 30 días;
- calcula correlación point-biserial y una prueba de permutación;
- genera tablas por segmento para apoyar la priorización de cartera.

La lectura recomendada es práctica: una relación significativa puede tener un efecto pequeño. Las decisiones deben complementarse con validación de negocio, política de crédito y otras variables de riesgo.

## Estructura

```text
morosidad-antiguedad-clientes/
├── .gitignore
├── README.md
├── historico_sintetico.csv
├── analisis_morosidad.py
├── generar_datos_sinteticos.py
└── generar_reporte.py
```

## Ejecución

No se requieren dependencias externas; basta Python 3.10+.

```powershell
python analisis_morosidad.py --input historico_sintetico.csv --outdir output --fecha-corte 2026-06-20 --mora-dias 30 --perm 1000
python generar_reporte.py --outdir output --report output/reporte_resultados.md
```

Para generar un nuevo dataset de demostración:

```powershell
python generar_datos_sinteticos.py --output historico_sintetico.csv
```

## Datos y confidencialidad

El repositorio incluye únicamente datos sintéticos. La estructura representa un escenario de crédito y cobranza, pero no contiene datos, clientes, documentos ni saldos de ninguna empresa. Los archivos generados en `output/` se excluyen del control de versiones.

## Tecnologías

Python, CSV, JSON y Markdown.

## Posibles extensiones

- Pruebas de sensibilidad con distintos umbrales de mora.
- Visualización del riesgo por segmento en Power BI.
- Modelo predictivo explicable, validado con el área de negocio.
