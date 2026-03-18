# V6: Logic signature abuse - Instance 2 (PATCHED)
# Fix: add a transaction lease (unique per period) to prevent replay.
# Lease is a 32-byte value set by the authorized sender; once the tx
# lands on-chain, the AVM rejects any transaction with the same lease
# from the same sender until the validity window expires.

from pyteal import *

MONTHLY_LIMIT = Int(1_000_000)
AUTHORIZED_RECEIVER = Addr("AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA")


def subscription_logsig() -> Expr:
    is_payment = Txn.type_enum() == TxnType.Payment
    amount_ok = Txn.amount() <= MONTHLY_LIMIT
    fee_ok = Txn.fee() <= Int(1000)
    # FIX: receiver constrained to authorized address.
    receiver_ok = Txn.receiver() == AUTHORIZED_RECEIVER
    # FIX: require a non-zero lease — prevents replay within the lease window.
    has_lease = Txn.lease() != Bytes("base16", "00" * 32)
    no_rekey = Txn.rekey_to() == Global.zero_address()
    no_close = Txn.close_remainder_to() == Global.zero_address()

    return And(is_payment, amount_ok, fee_ok, receiver_ok, has_lease, no_rekey, no_close)


if __name__ == "__main__":
    print(compileTeal(subscription_logsig(), mode=Mode.Signature, version=6))
