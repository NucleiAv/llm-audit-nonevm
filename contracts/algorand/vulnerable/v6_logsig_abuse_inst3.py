# V6: Logic signature abuse - Instance 3 (variant)
# Subtler: LogicSig uses a first-valid/last-valid window check as a
# "freshness" guard, but the window is wide enough (1000 rounds ~= 1 hour)
# that an attacker who captures the signed transaction bytes can resubmit
# them at any point within the validity window. No lease, no secret.

from pyteal import *

AUTHORIZED_RECEIVER = Addr("AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA")
MAX_WINDOW = Int(1000)  # rounds — approximately 1 hour on Algorand mainnet


def freshness_logsig() -> Expr:
    is_payment = Txn.type_enum() == TxnType.Payment
    fee_ok = Txn.fee() <= Int(1000)
    receiver_ok = Txn.receiver() == AUTHORIZED_RECEIVER
    # BUG: validity window check alone does not prevent replay within the window.
    # The signed transaction can be rebroadcast by any network observer
    # until last_valid is reached. No lease is set to deduplicate.
    window_ok = Txn.last_valid() - Txn.first_valid() <= MAX_WINDOW
    amount_ok = Txn.amount() <= Int(5_000_000)

    return And(is_payment, fee_ok, receiver_ok, window_ok, amount_ok)


if __name__ == "__main__":
    print(compileTeal(freshness_logsig(), mode=Mode.Signature, version=6))
