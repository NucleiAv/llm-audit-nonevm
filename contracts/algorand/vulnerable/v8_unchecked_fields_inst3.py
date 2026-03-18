# V8: Unchecked asset receiver and fee fields - Instance 3 (variant)
# Subtler: The contract checks receiver AND fee for the payment leg,
# but neglects to check close_remainder_to. An attacker sets
# close_remainder_to = attacker_address, which causes the AVM to send
# ALL remaining balance in the sender's account to the attacker after
# the payment, even though the payment amount check passed.

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
        # BUG: close_remainder_to not checked.
        # Attacker sets close_remainder_to = attacker_address, draining
        # the full account balance as a side effect of the payment.
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
