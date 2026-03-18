# V7: Group transaction manipulation - Instance 1 (PATCHED)
# Fix: use Txn.group_index() to reference the transaction immediately
# preceding the current app call, not a hardcoded index. Also enforce
# group size to prevent transaction insertion attacks.

from pyteal import *


def escrow_app() -> Expr:
    # FIX: use Txn.group_index() - 1 to reference the preceding transaction
    # relative to the current app call's position in the group.
    pay_index = Txn.group_index() - Int(1)

    payment_check = And(
        Gtxn[pay_index].type_enum() == TxnType.Payment,
        Gtxn[pay_index].receiver() == Global.current_application_address(),
        Gtxn[pay_index].amount() >= Int(1_000_000),
        # FIX: enforce exact group size to prevent insertion of extra transactions.
        Global.group_size() == Int(2),
    )

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
