from pyteal import *

def logsig_contract() -> Expr:
    is_payment = Txn.type_enum() == TxnType.Payment
    fee_ok = Txn.fee() <= Int(1000)

    return And(is_payment, fee_ok)

if __name__ == "__main__":
    print(compileTeal(logsig_contract(), mode=Mode.Signature, version=6))
