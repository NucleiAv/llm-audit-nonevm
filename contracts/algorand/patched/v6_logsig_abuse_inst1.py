# V6: Logic signature abuse - Instance 1 (PATCHED)
# Fix: constrain receiver to a hardcoded authorized address,
# require a hash preimage, limit rekey and close-remainder targets.

from pyteal import *

# Authorized receiver — only this address may receive from the escrow.
AUTHORIZED_RECEIVER = Addr("AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA")
# Expected secret hash (SHA-256 of the escrow secret).
EXPECTED_HASH = Bytes("base64", "47DEQpj8HBSa+/TImW+5JCeuQeRkm5NMpJWZG3hSuFU=")


def logsig_contract() -> Expr:
    is_payment = Txn.type_enum() == TxnType.Payment
    fee_ok = Txn.fee() <= Int(1000)
    # FIX: receiver must be the authorized address.
    receiver_ok = Txn.receiver() == AUTHORIZED_RECEIVER
    # FIX: no rekeying or close-remainder-to allowed.
    no_rekey = Txn.rekey_to() == Global.zero_address()
    no_close = Txn.close_remainder_to() == Global.zero_address()
    # FIX: caller must supply the correct secret preimage.
    secret_ok = Sha256(Arg(0)) == EXPECTED_HASH

    return And(is_payment, fee_ok, receiver_ok, no_rekey, no_close, secret_ok)


if __name__ == "__main__":
    print(compileTeal(logsig_contract(), mode=Mode.Signature, version=6))
