# V6: Logic signature abuse - Instance 2
# Pattern: Recurring payment LogicSig intended for a subscription service.
# Only checks that the payment amount is within a monthly limit and that
# the note field matches a specific string — both publicly observable.
# Any observer who records a valid transaction can replay it identically.

from pyteal import *

MONTHLY_LIMIT = Int(1_000_000)  # 1 ALGO in microalgos
EXPECTED_NOTE = Bytes("subscription-payment-v1")


def subscription_logsig() -> Expr:
    is_payment = Txn.type_enum() == TxnType.Payment
    amount_ok = Txn.amount() <= MONTHLY_LIMIT
    # BUG: note field is publicly visible on-chain.
    # Any observer can replay this exact transaction to drain the account.
    note_ok = Txn.note() == EXPECTED_NOTE
    fee_ok = Txn.fee() <= Int(1000)

    return And(is_payment, amount_ok, note_ok, fee_ok)


if __name__ == "__main__":
    print(compileTeal(subscription_logsig(), mode=Mode.Signature, version=6))
