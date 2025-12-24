from genetic_gp.core.logic import Implies, LVar
from genetic_gp.core.proofs import Proof, ProofStep

from learned_simplification import ExperimentConfig, ExperimentProblem, run_simplification_experiment


def test_runner_includes_proof_problem_results():
    p = LVar("P")
    q = LVar("Q")
    proof = Proof(
        [
            ProofStep(p, "assumption"),
            ProofStep(Implies(p, q), "assumption"),
            ProofStep(q, "modus_ponens", premises=(0, 1)),
        ]
    )
    config = ExperimentConfig(
        seed=123,
        problems=[
            ExperimentProblem(
                "Proof: modus ponens",
                kind="proof",
                proof=proof,
                expected_proof_valid=True,
            )
        ],
    )

    results, _, _ = run_simplification_experiment(config)

    assert results["problems"] == []
    assert results["proofs"]
    proof_result = results["proofs"][0]
    assert proof_result["name"] == "Proof: modus ponens"
    assert proof_result["valid"] is True
    assert proof_result["expected_valid"] is True
    assert proof_result["issues"] == []
