# V7: Group transaction manipulation - Instance 3 (variant)
# Subtler: The contract validates group index AND group size, but uses
# Gtxn[Txn.group_index() - 1] while failing to guard against group_index == 0.
# When the attacker sets group_index to 0, subtracting 1 wraps to the maximum
# group index (AVM uses modular arithmetic), pointing to an attacker-controlled
# transaction at the end of the group.

from pyteal import *


def lending_contract() -> Expr:
    group_size_ok = Global.group_size() == Int(2)

    # BUG: if the app call is at group_index 0, then group_index - 1 wraps
    # to the last slot (index 1 in a 2-tx group), which is also this app call.
    # The payment check then validates the app call itself as a payment — fails
    # badly or is trivially bypassed depending on AVM version.
    pay_index = Txn.group_index() - Int(1)

    payment_ok = And(
        Gtxn[pay_index].type_enum() == TxnType.Payment,
        Gtxn[pay_index].amount() >= Int(500_000),
        Gtxn[pay_index].receiver() == Global.current_application_address(),
    )

    return Seq(
        Assert(group_size_ok),
        Assert(payment_ok),
        Approve(),
    )


def approval_program() -> Expr:
    return Cond(
        [Txn.application_id() == Int(0), Approve()],
        [Txn.on_completion() == OnComplete.NoOp, lending_contract()],
    )


def clear_program() -> Expr:
    return Approve()


if __name__ == "__main__":
    print("Approval:")
    print(compileTeal(approval_program(), mode=Mode.Application, version=6))
