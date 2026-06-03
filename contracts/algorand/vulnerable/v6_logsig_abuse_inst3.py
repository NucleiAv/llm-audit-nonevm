from pyteal import *

AUTHORIZED_RECEIVER = Addr("AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA")
MAX_WINDOW = Int(1000)

def freshness_logsig() -> Expr:
    is_payment = Txn.type_enum() == TxnType.Payment
    fee_ok = Txn.fee() <= Int(1000)
    receiver_ok = Txn.receiver() == AUTHORIZED_RECEIVER
    window_ok = Txn.last_valid() - Txn.first_valid() <= MAX_WINDOW
    amount_ok = Txn.amount() <= Int(5_000_000)

    return And(is_payment, fee_ok, receiver_ok, window_ok, amount_ok)

if __name__ == "__main__":
    print(compileTeal(freshness_logsig(), mode=Mode.Signature, version=6))
