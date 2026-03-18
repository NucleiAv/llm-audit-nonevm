# V8: Unchecked asset receiver and fee fields - Instance 2
# Pattern: A payment contract allows users to specify the fee field.
# The contract checks the payment amount and receiver but permits
# arbitrarily high user-supplied fees that drain the sender's account.

from pyteal import *

MERCHANT = Addr("AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA")
PAYMENT_AMOUNT = Int(5_000_000)


def payment_contract() -> Expr:
    payment_check = And(
        Gtxn[0].type_enum() == TxnType.Payment,
        Gtxn[0].receiver() == MERCHANT,
        Gtxn[0].amount() == PAYMENT_AMOUNT,
        # BUG: fee field not checked. User can set fee = 1_000_000_000 microalgos,
        # draining their own account far beyond the payment amount, or in a
        # shared-fee scenario, draining a pooled fee account.
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
