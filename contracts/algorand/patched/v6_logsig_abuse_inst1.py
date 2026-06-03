from pyteal import *

AUTHORIZED_RECEIVER = Addr("AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA")
EXPECTED_HASH = Bytes("base64", "47DEQpj8HBSa+/TImW+5JCeuQeRkm5NMpJWZG3hSuFU=")

def logsig_contract() -> Expr:
    is_payment = Txn.type_enum() == TxnType.Payment
    fee_ok = Txn.fee() <= Int(1000)
    receiver_ok = Txn.receiver() == AUTHORIZED_RECEIVER
    no_rekey = Txn.rekey_to() == Global.zero_address()
    no_close = Txn.close_remainder_to() == Global.zero_address()
    secret_ok = Sha256(Arg(0)) == EXPECTED_HASH

    return And(is_payment, fee_ok, receiver_ok, no_rekey, no_close, secret_ok)

if __name__ == "__main__":
    print(compileTeal(logsig_contract(), mode=Mode.Signature, version=6))
