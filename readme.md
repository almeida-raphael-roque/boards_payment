> **⚠️ For confidentiality and information security reasons, this repository has had sensitive data, names, and details removed or changed. All confidential or strategic information has been intentionally suppressed or obfuscated. This material is for demonstration purposes only. ⚠️**

# License Plate Payment Status Report

Automated ETL pipeline that consolidates vehicle-level invoice payment status across multiple business units for collections and finance teams.

---

## Project Overview

This project generates a recurring **payment status report** at the **license plate** level. It connects financial records (boletos) to active insurance policies and classifies each entry as paid, recently overdue, or overdue by 45 days or more.

**Business problem:** Collections and operations need a single, up-to-date Excel dataset to monitor which insured vehicles are current on payments versus overdue—without manual cross-checking across ERP schemas and brands.

**Outcome:** A unified dataset exported to Excel, ready for dashboards, follow-up workflows, and stakeholder review.

---

## Technologies Used

| Area | Stack |
|------|--------|
| Language | **Python 3** |
| Query layer | **SQL** (AWS Athena / Presto) |
| Data lake | **AWS Athena** (`silver` + brand-specific schemas) |
| Processing | **Pandas** |
| Prototyping | **Jupyter Notebook** |
| Export | **Excel** via **openpyxl** |
| AWS integration | **AWS Wrangler** (`awswrangler`) |

---

## Key Libraries

| Library | Role in this project |
|---------|----------------------|
| **awswrangler** | Runs external SQL files against Athena and returns DataFrames |
| **pandas** | Filters, anti-joins, labeling, and concatenation of result sets |
| **openpyxl** | Writes the final `.xlsx` report |
| **datetime** | Execution timestamps and run-duration logging in the production script |

---

## Data Processing & SQL Logic

Three parameterized SQL assets drive extraction:

| Query | Purpose |
|-------|---------|
| `faturas_baixadas.sql` | Paid / settled titles (**adimplentes**) |
| `faturas_posvencimento_recente.sql` | Overdue **1–44 days** after due date |
| `faturas_posvencimento_45.sql` | Overdue **45+ days** after due date |

**High-level SQL design:**

- **Multi-brand `UNION ALL`** across four operational schemas (e.g. Segtruck, Stcoop, Viavante, Tag).
- **Core joins:** financial titles → customer catalog → insurance invoice/set → vehicle/trailer assets (plate and chassis via `COALESCE`).
- **Settlement subquery** (`faturas_baixadas`): aggregates write-offs by `ponteiro` with cash-flow and receivable filters.
- **Overdue filters:** `DATE_DIFF` on due date vs. `current_date`; non-consolidated pointers; receivable flag `crc_cpg = 'R'`.
- **Shared business filters:** active policy/coverage status, valid plate and chassis, selected financial application codes, rolling emission window.

**Python-side rules (post-SQL):**

- **Anti-join:** remove overdue rows whose `(ponteiro, empresa, conjunto)` already appears in the paid set.
- **Collections exclusions:** drop specific associate patterns and test accounts from overdue bases.
- **Status label:** `adimplente` | `inadimplente` | `inadimplente 45+`.
- **Merge:** single DataFrame via `pd.concat` for export.

---

## Analysis & Notebook Logic

`ipynb/ETL_geral.ipynb` documents the original exploratory workflow; `python/ETL_placas_adimp.py` is the productionized version.

| Step | Description |
|------|-------------|
| **Extraction** | Load SQL from disk → execute on Athena → three DataFrames |
| **Reconciliation** | Build a set of paid invoice keys; filter overdue datasets |
| **Cleaning** | Apply collections-driven exclusion rules |
| **Feature engineering** | Add `pagamento` category column |
| **Output** | Concatenate and write `relatorio_adimplencia_inadimplencia.xlsx` (replace-if-exists) |

The Python class (`ETL_relat_placas_adimp`) adds structured logging, error handling, and a single `run()` orchestrator.

---

## Key Highlights

- **Multi-tenant data lake queries** spanning several ERP schemas with identical business logic per brand.
- **Reconciliation pattern** that prevents double-counting paid titles in overdue buckets (composite key lookup).
- **Complex relational modeling** in SQL: finance × insurance × fleet assets in one grain (plate + title).
- **Notebook → script refactor** for repeatable, schedulable execution.
- **Operational efficiency:** replaces manual Excel assembly with an automated, logged pipeline.

---

## Project Structure

```
sql/                          # Athena extraction queries
python/ETL_placas_adimp.py    # Production ETL class
ipynb/ETL_geral.ipynb         # Prototype / validation notebook
```

---

## Running (illustrative)

```bash
python python/ETL_placas_adimp.py
```

Requires AWS credentials configured for Athena and access to the target database/schemas.
