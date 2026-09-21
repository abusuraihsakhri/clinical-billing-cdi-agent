import csv
from pathlib import Path

from cdi_sentinel import (
    CDICoordinator,
    DocumentationGapScannerAgent,
    DomainKnowledgeRegistry,
    HCCRiskWeightCalculatorAgent,
    PhysicianQuerySynthesizerAgent,
    main,
)


def test_sub_agents():
    assert len(DocumentationGapScannerAgent().evaluate({"metric_primary": 35.0})) == 1
    assert len(HCCRiskWeightCalculatorAgent().evaluate({"critical_flag": True})) == 1
    assert len(PhysicianQuerySynthesizerAgent().evaluate({"status_text": "DISCORDANT_FINDING"})) == 1


def test_false_string_does_not_trigger_priority():
    alerts = HCCRiskWeightCalculatorAgent().evaluate({
        "critical_flag": "False",
        "metric_secondary": 2.0,
    })
    assert alerts == []


def test_coordinator():
    coord = CDICoordinator()
    dossier = coord.audit_case({
        "case_id": "TEST-100",
        "metric_primary": 10.0,
        "metric_secondary": 2.0,
        "critical_flag": "False",
    })
    assert dossier["overall_status"] == "CONCORDANT_NORMAL"
    assert dossier["total_alerts"] == 0

    answer = coord.query_assistant("What are the guidelines?")
    assert "external model" in answer.lower() or "deterministic" in answer.lower()


def test_cli():
    assert main(["audit", "--case-id", "CLI-01"]) == 0
    assert main(["chat", "What", "is", "the", "system", "status?"]) == 0


def test_batch_false_boolean(tmp_path: Path):
    source = tmp_path / "input.csv"
    output = tmp_path / "output.csv"
    source.write_text(
        "case_id,metric_primary,metric_secondary,critical_flag,status_text\n"
        "C1,10,2,False,NORMAL\n",
        encoding="utf-8",
    )
    assert main(["batch", "-i", str(source), "-o", str(output)]) == 0
    with output.open(newline="", encoding="utf-8") as handle:
        row = next(csv.DictReader(handle))
    assert row["critical_count"] == "0"


def test_domain_registry_is_truthful_about_scope():
    assert DomainKnowledgeRegistry.ZERO_PHI_COMPLIANCE is False
    assert DomainKnowledgeRegistry.HIPAA_SAFE_HARBOR == "NOT_CLAIMED"
    assert DomainKnowledgeRegistry.SYSTEM_VERSION == "2.1.0"
