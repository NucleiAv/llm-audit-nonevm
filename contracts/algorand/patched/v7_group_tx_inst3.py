from pyteal import *

PAYMENT_INDEX = Int(0)
APP_CALL_INDEX = Int(1)

def lending_contract() -> Expr:
    group_size_ok = Global.group_size() == Int(2)

    this_call_is_second = Txn.group_index() == APP_CALL_INDEX

    payment_ok = And(
        Gtxn[PAYMENT_INDEX].type_enum() == TxnType.Payment,
        Gtxn[PAYMENT_INDEX].amount() >= Int(500_000),
        Gtxn[PAYMENT_INDEX].receiver() == Global.current_application_address(),
    )

    return Seq(
        Assert(group_size_ok),
        Assert(this_call_is_second),
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
