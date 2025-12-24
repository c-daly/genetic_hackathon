from genetic_gp.core.logic import And, Implies, LVar, Not, Or
from genetic_gp.core.proofs import Proof, ProofStep


def test_proof_modus_ponens():
    p = LVar("P")
    q = LVar("Q")
    proof = Proof(
        [
            ProofStep(p, "assumption"),
            ProofStep(Implies(p, q), "assumption"),
            ProofStep(q, "modus_ponens", (0, 1)),
        ]
    )

    ok, issues = proof.verify()

    assert ok is True
    assert issues == []


def test_proof_and_or_steps():
    p = LVar("P")
    q = LVar("Q")
    proof = Proof(
        [
            ProofStep(p, "assumption"),
            ProofStep(q, "assumption"),
            ProofStep(And(p, q), "and_intro", (0, 1)),
            ProofStep(p, "and_elim_left", (2,)),
            ProofStep(Or(p, q), "or_intro", (3,)),
        ]
    )

    ok, issues = proof.verify()

    assert ok is True
    assert issues == []


def test_proof_equivalence_and_double_negation():
    p = LVar("P")
    q = LVar("Q")
    proof = Proof(
        [
            ProofStep(p, "assumption"),
            ProofStep(Not(Not(p)), "double_negation_intro", (0,)),
            ProofStep(p, "double_negation_elim", (1,)),
            ProofStep(Or(p, q), "equivalence", (1,)),
        ]
    )

    ok, issues = proof.verify()

    assert ok is False
    assert any(issue.rule == "equivalence" for issue in issues)
