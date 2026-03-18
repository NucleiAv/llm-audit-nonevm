# V6: Logic signature abuse - Instance 1
# Source: De Angelis et al. (IEEE DAPPS 2022); Boi & Esposito (BCCA 2025).
# Vulnerability: This LogicSig approves any payment transaction where the
# fee is below 1000 microalgos. It does not check the receiver, the sender,
# or require any secret knowledge from the caller. Any party who obtains
# or reverse-engineers the TEAL bytecode can use it to sign arbitrary
# payment transactions from the escrow account up to the fee limit.

from pyteal import *


def logsig_contract() -> Expr:
    # BUG: only fee is checked. No receiver check, no sender check,
    # no secret/hash preimage requirement, and no lease/rekey guard.
    # Attacker obtains the compiled TEAL, reuses it to drain the escrow.
    is_payment = Txn.type_enum() == TxnType.Payment
    fee_ok = Txn.fee() <= Int(1000)

    return And(is_payment, fee_ok)


if __name__ == "__main__":
    print(compileTeal(logsig_contract(), mode=Mode.Signature, version=6))
