# V7: Group transaction manipulation - Instance 2
# Pattern: A DEX swap contract checks group membership but not group size.
# An attacker wraps the swap call in a larger atomic group that includes
# additional asset transfers, enabling frontrunning or fee extraction
# by inserting extra transactions around the expected swap pair.

from pyteal import *

DEX_APP_ID = Int(999999)


def swap_contract() -> Expr:
    # BUG: checks that Gtxn[0] is an asset transfer and Gtxn[1] is this call,
    # but does not assert Global.group_size() == 2.
    # Attacker can insert Gtxn[2], Gtxn[3], ... without triggering rejection.
    asset_transfer_ok = And(
        Gtxn[0].type_enum() == TxnType.AssetTransfer,
        Gtxn[0].asset_receiver() == Global.current_application_address(),
        Gtxn[0].xfer_asset() == Txn.assets[0],
    )

    app_call_ok = And(
        Gtxn[1].type_enum() == TxnType.ApplicationCall,
        Gtxn[1].application_id() == DEX_APP_ID,
    )

    # No group size check — extra transactions silently allowed.
    return Seq(
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
