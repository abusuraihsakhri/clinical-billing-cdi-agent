# Clinical Billing & CDI Agent (CDI-Sentinel)

> **Domain:** Health Information Management, Clinical Documentation Improvement (CDI), and CMS-HCC Risk Adjustment  
> **Reference Standards:** CMS-HCC Risk Adjustment Model v28/v24, ACDIS/AHIMA Clinical Documentation Guidelines, Official ICD-10-CM Coding Guidelines, HIPAA Safe Harbor Privacy Rule

<div align="center">

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
![Python](https://img.shields.io/badge/Python-3.10%20%7C%203.11%20%7C%203.12-3776AB.svg?logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.111-009688.svg?logo=fastapi&logoColor=white)
![Audit Trail](https://img.shields.io/badge/Audit-HMAC--SHA256_Tamper--Evident-brightgreen.svg)
![Zero-PHI Guard](https://img.shields.io/badge/Guard-Zero--PHI_Outbound-blue.svg)

</div>

---

## 📖 Executive Summary & Clinical Context

**Clinical Billing CDI Agent (`CDI-Sentinel`)** is an automated clinical documentation improvement and hierarchical condition category (HCC) risk-adjustment surveillance engine. In modern value-based care and prospective payment systems (such as Medicare Advantage and Inpatient Prospective Payment Systems [IPPS]), documentation omissions directly compromise risk score accuracy, physician query compliance, and appropriate hospital reimbursement.

The system performs:
1. **Clinical Documentation Gap Scanning:** Detects uncaptured MCC/CC (Major Complication/Comorbidity) opportunities from clinical parameters.
2. **CMS-HCC Risk Score Optimization:** Calculates hierarchical risk coefficients and projects risk-adjustment impact.
3. **Non-Leading Physician Query Synthesis:** Generates compliant physician clarification queries adhering strictly to ACDIS/AHIMA standards.
4. **Zero-PHI Interception & Tamper-Evident HMAC Audit Trails:** Enforces strict HIPAA Safe Harbor de-identification before any reasoning or logging occurs.

---

## 📐 Clinical & Domain Formulations

### 1. CMS-HCC Risk Adjustment Factor (RAF) Score Calculation

The aggregated Risk Adjustment Factor ($RAF$) score for a patient encounter is modeled by summing demographic factors, baseline disease categories, and disease interaction increments:

$$\text{RAF}_{\text{total}} = \beta_{\text{demographic}} + \sum_{k \in \text{HCC}} w_k \cdot \mathbb{I}(k) + \sum_{(i,j) \in \text{Interactions}} \gamma_{ij} \cdot \mathbb{I}(i) \cdot \mathbb{I}(j)$$

Where:
- $\beta_{\text{demographic}}$: Base risk weight dictated by patient age, sex, Medicaid dual status, and original Medicare entitlement reason.
- $w_k$: Relative risk weight for Hierarchical Condition Category $k$.
- $\mathbb{I}(k) \in \{0, 1\}$: Binary indicator whether disease condition $k$ is supported by clinical chart documentation.
- $\gamma_{ij}$: Additional disease-to-disease interaction coefficient (e.g., Diabetes + Congestive Heart Failure).

### 2. Comorbidity Capture Completeness Index (CCCI)

$$\text{CCCI} = \frac{\sum_{i=1}^{N} \text{Validated CC/MCC Elements}_i}{\sum_{i=1}^{N} \text{Suspected Clinical Indicators}_i} \times 100\%$$

A $\text{CCCI} < 85\%$ triggers automated CDI review workflows for potential documentation discordance.

### 3. Financial & Revenue Yield Differential

$$\Delta \text{Revenue} = \Delta \text{RAF} \times \text{Base Rate} \times \text{Coding Normalization Factor}$$

---

## 📊 Reference Diagnostic Criteria & Risk Weight Matrix

| Category Code | Clinical Condition | Typical Severity Tier | Relative Risk Weight ($w_k$) | Documentation Gap Check |
|:---|:---|:---:|:---:|:---|
| **HCC 18** | Diabetes with Chronic Complications | CC / Moderate | $0.302 - 0.368$ | Specificity of end-organ involvement (nephropathy, neuropathy) |
| **HCC 85** | Congestive Heart Failure (Systolic/Diastolic) | CC / High | $0.331 - 0.380$ | Acuity (Acute, Chronic, Acute-on-Chronic), ejection fraction |
| **HCC 96** | Specified Heart Arrhythmias (Atrial Fibrillation) | CC / Moderate | $0.278$ | Persistent vs. paroxysmal vs. chronic atrial fibrillation |
| **HCC 136** | Chronic Kidney Disease (Stage 4, 5, ESRD) | CC / High | $0.289 - 0.521$ | GFR baseline staging; linkage to hypertensive etiology |
| **MCC** | Severe Sepsis / Septic Shock / Acute Organ Failure | MCC / STAT | $0.780 - 1.250$ | Clinical lactate kinetics, organ dysfunction criteria, SOFA |

---

## ⚙️ Architectural Sub-Agent Hierarchy

```
+-------------------------------------------------------------------------+
|                      SystemSupervisor / CDICoordinator                  |
|                 (Consensus Arbitration & Zero-PHI Guard)                |
+--------------------+--------------------+-------------------------------+
                     |                    |
                     v                    v
+--------------------+---+  +-------------+-------+  +--------------------+---+
| DocumentationGapScanner |  | SafetyEscalation    |  | ProtocolConformance|
|      (QC Worker)       |  |   (Safety Worker)   |  | (Physician Query)  |
| - Primary Metric Audit |  | - STAT Kinetics     |  | - Spec Concordance |
| - CC/MCC Discovery     |  | - Interlock Alerts  |  | - Query Validation |
+--------------------+---+  +-------------+-------+  +--------------------+---+
                     \                    |                   /
                      \                   |                  /
                       +------------------v-----------------+
                       |    HMAC-SHA256 Cryptographic Log   |
                       |       Tamper-Evident Blockchain    |
                       +------------------------------------+
```

---

## 💻 CLI Quickstart & Usage

The application provides a command-line interface supporting single-case auditing, supervisory interactive queries, cryptographic integrity verification, and high-throughput CSV batch evaluation.

### 1. Single Clinical Case Audit
```bash
python cli.py audit --task-id CASE-2026-001 --target SYNTH-PT-881 --primary 28.5 --secondary 14.2 --status DISCORDANT --critical
```

### 2. Supervisory Clarification Query (Chat)
```bash
python cli.py chat "Explain ACDIS documentation compliance criteria for acute respiratory failure"
```

### 3. Cryptographic Audit Verification
```bash
python cli.py verify-audit
```

### 4. High-Throughput Batch Processing
Process clinical records directly from a CSV file:
```bash
python cli.py batch -i sample.csv -o out_results.csv
```
Or using explicit long arguments:
```bash
python cli.py batch --input sample.csv --output out_results.csv
```

### Parameter Reference

| Command | Option | Description | Default |
|:---|:---|:---|:---|
| `audit` | `--task-id` | Unique task/case identifier | `TASK-2026-001` |
| `audit` | `--target` | Patient synthetic identifier / target | `KEY-TARGET-01` |
| `audit` | `--primary` | Primary clinical metric or risk index | `28.5` |
| `audit` | `--secondary` | Secondary kinetic parameter or score | `14.2` |
| `audit` | `--status` | Diagnostic concordance descriptor | `DISCORDANT` |
| `audit` | `--critical` | Flag for STAT clinical emergency | `False` |
| `batch` | `-i`, `--input` | Input CSV filepath containing case rows | Required |
| `batch` | `-o`, `--output` | Output CSV destination for enriched audit | `results.csv` |
| `serve` | `--host` / `--port` | Host address and port for FastAPI server | `127.0.0.1:8000` |

---

## 📋 Batch CSV Data Schema

The `sample.csv` and batch pipeline support both clinical HIM schemas and task-oriented records:

| Field | Type | Description | Example |
|:---|:---:|:---|:---|
| `case_id` / `task_id` | String | Unique encounter or chart identifier | `CASE-001` |
| `patient_synthetic_id` / `target_identifier` | String | De-identified synthetic patient token | `SYNTH-01` |
| `metric_primary` / `primary_metric` | Float | Primary clinical biomarker / risk measurement | `25.4` |
| `metric_secondary` / `secondary_metric` | Float | Secondary kinetic parameter or severity score | `14.2` |
| `is_stat` / `is_critical_flag` | Boolean | Priority triage indicator (`True`/`False`) | `True` |
| `status_flag` / `status_descriptor` | String | Diagnostic concordance state | `DISCORDANT` |

The batch process appends clinical surveillance results:
- `overall_urgency`: Evaluated urgency tier (`ROUTINE`, `ELEVATED_RISK`, `CRITICAL_STAT_PANIC`).
- `integrity_status`: Diagnostic concordance verification (`VALIDATED_OPTIMAL`, `DISCORDANT_ANOMALY`, `RECALIBRATION_REQUIRED`).
- `total_alerts`: Number of sub-agent clinical alerts raised.
- `audit_hash`: HMAC-SHA256 tamper-evident integrity signature.

---

## 🧪 Testing & Verification

Run the comprehensive pytest test suite:
```bash
python -m pytest -p no:zarr -v
```

Execute a CLI batch smoke test:
```bash
python cli.py batch -i sample.csv -o out_smoke.csv
python -c "import os; assert os.path.exists('out_smoke.csv'); os.remove('out_smoke.csv')"
```

---

## 🛡️ Zero-PHI Compliance & Auditability

- **HIPAA Safe Harbor Compliance:** Regex and AST interceptors automatically block 18 HIPAA Safe Harbor direct identifiers (Social Security Numbers, Medical Record Numbers, Names, Phone Numbers).
- **Tamper-Evident SHA-256 Audit Trail:** Every clinical audit event, parameter mutation, and supervisory action generates a sequentially chained cryptographic digest.

---

## 📜 License

Distributed under the MIT License. See [LICENSE](LICENSE) for details.
