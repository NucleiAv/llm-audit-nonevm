from pyteal import *

def escrow_app() -> Expr:
    payment_check = And(
        Gtxn[0].type_enum() == TxnType.Payment,
        Gtxn[0].receiver() == Global.current_application_address(),
        Gtxn[0].amount() >= Int(1_000_000),
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
