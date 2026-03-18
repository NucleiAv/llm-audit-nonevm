# V8: Unchecked asset receiver and fee fields - Instance 1 (PATCHED)
# Fix: assert asset_receiver equals the protocol treasury address.

from pyteal import *

EXPECTED_ASSET_ID = Int(12345678)
MIN_TRANSFER_AMOUNT = Int(1_000_000)
TREASURY = Addr("AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA")


def asset_vault() -> Expr:
    asset_check = And(
        Gtxn[0].type_enum() == TxnType.AssetTransfer,
        Gtxn[0].xfer_asset() == EXPECTED_ASSET_ID,
        Gtxn[0].asset_amount() >= MIN_TRANSFER_AMOUNT,
        # FIX: enforce the receiver is the protocol treasury.
        Gtxn[0].asset_receiver() == TREASURY,
        # FIX: no asset close-to allowed.
        Gtxn[0].asset_close_to() == Global.zero_address(),
    )

    return Seq(
        Assert(Global.group_size() == Int(2)),
        Assert(asset_check),
        Approve(),
    )


def approval_program() -> Expr:
    return Cond(
        [Txn.application_id() == Int(0), Approve()],
        [Txn.on_completion() == OnComplete.NoOp, asset_vault()],
    )


def clear_program() -> Expr:
    return Approve()


if __name__ == "__main__":
    print("Approval:")
    print(compileTeal(approval_program(), mode=Mode.Application, version=6))
