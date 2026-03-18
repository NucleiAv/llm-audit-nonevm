# V8: Unchecked asset receiver and fee fields - Instance 3 (PATCHED)
# Fix: assert close_remainder_to == zero_address to prevent account draining.

from pyteal import *

PROTOCOL = Addr("AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA")
PAYMENT_AMOUNT = Int(2_000_000)
MAX_FEE = Int(1000)


def staking_contract() -> Expr:
    payment_check = And(
        Gtxn[0].type_enum() == TxnType.Payment,
        Gtxn[0].receiver() == PROTOCOL,
        Gtxn[0].amount() == PAYMENT_AMOUNT,
        Gtxn[0].fee() <= MAX_FEE,
        # FIX: close_remainder_to must be the zero address — prevents draining.
        Gtxn[0].close_remainder_to() == Global.zero_address(),
        # FIX: rekey_to must also be zero to prevent account rekeying.
        Gtxn[0].rekey_to() == Global.zero_address(),
    )

    return Seq(
        Assert(Global.group_size() == Int(2)),
        Assert(payment_check),
        Approve(),
    )


def approval_program() -> Expr:
    return Cond(
        [Txn.application_id() == Int(0), Approve()],
        [Txn.on_completion() == OnComplete.NoOp, staking_contract()],
    )


def clear_program() -> Expr:
    return Approve()


if __name__ == "__main__":
    print("Approval:")
    print(compileTeal(approval_program(), mode=Mode.Application, version=6))
