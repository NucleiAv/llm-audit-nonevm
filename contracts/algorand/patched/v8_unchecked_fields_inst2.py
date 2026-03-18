# V8: Unchecked asset receiver and fee fields - Instance 2 (PATCHED)
# Fix: cap the fee to a safe maximum (1000 microalgos = standard fee).

from pyteal import *

MERCHANT = Addr("AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA")
PAYMENT_AMOUNT = Int(5_000_000)
MAX_FEE = Int(1000)


def payment_contract() -> Expr:
    payment_check = And(
        Gtxn[0].type_enum() == TxnType.Payment,
        Gtxn[0].receiver() == MERCHANT,
        Gtxn[0].amount() == PAYMENT_AMOUNT,
        # FIX: fee bounded to prevent account draining.
        Gtxn[0].fee() <= MAX_FEE,
        # FIX: no close-remainder-to address allowed.
        Gtxn[0].close_remainder_to() == Global.zero_address(),
    )

    return Seq(
        Assert(Global.group_size() == Int(2)),
        Assert(payment_check),
        Approve(),
    )


def approval_program() -> Expr:
    return Cond(
        [Txn.application_id() == Int(0), Approve()],
        [Txn.on_completion() == OnComplete.NoOp, payment_contract()],
    )


def clear_program() -> Expr:
    return Approve()


if __name__ == "__main__":
    print("Approval:")
    print(compileTeal(approval_program(), mode=Mode.Application, version=6))
