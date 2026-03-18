# V7: Group transaction manipulation - Instance 1
# Source: Algorand Foundation developer security guidance; Boi & Esposito (BCCA 2025).
# Vulnerability: The contract checks that a payment transaction exists in the group
# but does not verify its index position. An attacker inserts the required payment
# at index 0 and places a no-op transaction at index 1 where the contract expects
# to be evaluated, causing the payment check to reference the wrong group member.

from pyteal import *


def escrow_app() -> Expr:
    # BUG: checks Gtxn[0] unconditionally, assumes the payment is always first.
    # Attacker rearranges group: puts their own transaction at index 0
    # (passing the payment check) and moves the real trigger to index 1.
    payment_check = And(
        Gtxn[0].type_enum() == TxnType.Payment,
        Gtxn[0].receiver() == Global.current_application_address(),
        Gtxn[0].amount() >= Int(1_000_000),
    )

    # This app call is evaluated as Gtxn[1] per the attacker's arrangement.
    # The payment check above passes because Gtxn[0] is the attacker's payment.
    on_release = Seq(
        Assert(payment_check),
        Approve(),
    )

    return on_release


def approval_program() -> Expr:
    return Cond(
        [Txn.application_id() == Int(0), Approve()],
        [Txn.on_completion() == OnComplete.NoOp, escrow_app()],
    )


def clear_program() -> Expr:
    return Approve()


if __name__ == "__main__":
    print("Approval:")
    print(compileTeal(approval_program(), mode=Mode.Application, version=6))
    print("\nClear:")
    print(compileTeal(clear_program(), mode=Mode.Application, version=6))
