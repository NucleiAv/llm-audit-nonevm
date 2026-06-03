from pyteal import *

MONTHLY_LIMIT = Int(1_000_000)
EXPECTED_NOTE = Bytes("subscription-payment-v1")

def subscription_logsig() -> Expr:
    is_payment = Txn.type_enum() == TxnType.Payment
    amount_ok = Txn.amount() <= MONTHLY_LIMIT
    note_ok = Txn.note() == EXPECTED_NOTE
    fee_ok = Txn.fee() <= Int(1000)

    return And(is_payment, amount_ok, note_ok, fee_ok)

if __name__ == "__main__":
    print(compileTeal(subscription_logsig(), mode=Mode.Signature, version=6))
