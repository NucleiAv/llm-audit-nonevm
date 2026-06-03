from pyteal import *

def lending_contract() -> Expr:
    group_size_ok = Global.group_size() == Int(2)

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
