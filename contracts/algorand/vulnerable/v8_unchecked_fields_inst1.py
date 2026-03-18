# V8: Unchecked asset receiver and fee fields - Instance 1
# Source: Boi & Esposito (BCCA 2025); Algorand Foundation security guidance.
# Vulnerability: The contract validates the asset transfer amount but does not
# check the asset_receiver field. An attacker sets asset_receiver to their own
# address in the transaction they submit, redirecting the asset transfer away
# from the intended protocol treasury.

from pyteal import *

EXPECTED_ASSET_ID = Int(12345678)
MIN_TRANSFER_AMOUNT = Int(1_000_000)


def asset_vault() -> Expr:
    # BUG: validates amount and asset ID but not the receiver.
    # Attacker sets xfer_asset = EXPECTED_ASSET_ID, asset_amount >= minimum,
    # but asset_receiver = attacker_address to steal the transferred assets.
    asset_check = And(
        Gtxn[0].type_enum() == TxnType.AssetTransfer,
        Gtxn[0].xfer_asset() == EXPECTED_ASSET_ID,
        Gtxn[0].asset_amount() >= MIN_TRANSFER_AMOUNT,
        # MISSING: Gtxn[0].asset_receiver() check
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
