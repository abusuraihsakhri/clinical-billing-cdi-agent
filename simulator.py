"""Local stress/smoke simulator for the deterministic rule workflow."""
import random
import sys
import time

from agents.base import AuditLogger, PHIGuard, SecurityException
from agents.models import SystemTaskPayload
from agents.supervisor import SystemSupervisor


def run_simulation(iterations: int = 100, seed: int = 42):
    if iterations <= 0:
        raise ValueError("iterations must be greater than zero")

    rng = random.Random(seed)
    print(f"Starting local rule simulation ({iterations} tasks, seed={seed})...")
    supervisor = SystemSupervisor(model_provider="mock")
    start_time = time.time()
    nominal_count = 0
    elevated_count = 0
    critical_count = 0
    identifier_guard_checks = 0
    identifier_guard_blocks = 0

    for i in range(iterations):
        payload = SystemTaskPayload(
            task_id=f"SIM-{i + 1:04d}",
            target_identifier=f"SPECIMEN-{rng.randint(100, 999)}",
            primary_metric=round(rng.uniform(5.0, 40.0), 2),
            secondary_metric=round(rng.uniform(1.0, 20.0), 2),
            status_descriptor=rng.choice(["NOMINAL", "DISCORDANT_ANOMALY", "SUSPICIOUS", "OPTIMAL"]),
            is_critical_flag=rng.random() < 0.15,
        )

        dossier = supervisor.process_task(payload)
        if dossier.overall_urgency.value == "CRITICAL_STAT_PANIC":
            critical_count += 1
        elif dossier.overall_urgency.value == "ELEVATED_RISK":
            elevated_count += 1
        else:
            nominal_count += 1

        if (i + 1) % 25 == 0:
            identifier_guard_checks += 1
            try:
                PHIGuard.assert_no_phi(f"Patient MRN-{rng.randint(100000, 999999)} test")
            except SecurityException:
                identifier_guard_blocks += 1

    elapsed = time.time() - start_time
    rate = iterations / max(0.001, elapsed)
    print("\n" + "=" * 64)
    print("SIMULATION SUMMARY")
    print("=" * 64)
    print(f"Tasks processed:            {iterations}")
    print(f"Elapsed:                    {elapsed:.3f}s ({rate:.1f} tasks/s)")
    print(f"Routine outcomes:           {nominal_count}")
    print(f"Elevated outcomes:          {elevated_count}")
    print(f"Priority outcomes:          {critical_count}")
    print(f"Identifier guard examples:  {identifier_guard_blocks}/{identifier_guard_checks} blocked")
    print(f"Audit records:              {len(AuditLogger.get_trail())}")
    print(f"Audit integrity check:      {AuditLogger.verify_integrity()}")
    print("=" * 64)


if __name__ == "__main__":
    count = int(sys.argv[1]) if len(sys.argv) > 1 else 100
    run_simulation(count)
