# V7: Group transaction manipulation - Instance 2 (PATCHED)
# Fix: assert Global.group_size() == 2 to prevent transaction insertion.

from pyteal import *

DEX_APP_ID = Int(999999)


def swap_contract() -> Expr:
    asset_transfer_ok = And(
        Gtxn[0].type_enum() == TxnType.AssetTransfer,
        Gtxn[0].asset_receiver() == Global.current_application_address(),
        Gtxn[0].xfer_asset() == Txn.assets[0],
    )

    app_call_ok = And(
        Gtxn[1].type_enum() == TxnType.ApplicationCall,
        Gtxn[1].application_id() == DEX_APP_ID,
    )

    # FIX: exact group size enforced — no extra transactions permitted.
    group_size_ok = Global.group_size() == Int(2)

    return Seq(
        Assert(group_size_ok),
        Assert(asset_transfer_ok),
        Assert(app_call_ok),
        Approve(),
    )


def approval_program() -> Expr:
    return Cond(
        [Txn.application_id() == Int(0), Approve()],
        [Txn.on_completion() == OnComplete.NoOp, swap_contract()],
    )


def clear_program() -> Expr:
    return Approve()


if __name__ == "__main__":
    print("Approval:")
    print(compileTeal(approval_program(), mode=Mode.Application, version=6))
