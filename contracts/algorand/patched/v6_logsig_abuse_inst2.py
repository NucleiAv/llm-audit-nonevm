from pyteal import *

MONTHLY_LIMIT = Int(1_000_000)
AUTHORIZED_RECEIVER = Addr("AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA")

def subscription_logsig() -> Expr:
    is_payment = Txn.type_enum() == TxnType.Payment
    amount_ok = Txn.amount() <= MONTHLY_LIMIT
    fee_ok = Txn.fee() <= Int(1000)
    receiver_ok = Txn.receiver() == AUTHORIZED_RECEIVER
    has_lease = Txn.lease() != Bytes("base16", "00" * 32)
    no_rekey = Txn.rekey_to() == Global.zero_address()
    no_close = Txn.close_remainder_to() == Global.zero_address()

    return And(is_payment, amount_ok, fee_ok, receiver_ok, has_lease, no_rekey, no_close)

if __name__ == "__main__":
    print(compileTeal(subscription_logsig(), mode=Mode.Signature, version=6))
