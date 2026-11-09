import os

from web3 import Web3


ETH_RPC_URL = os.getenv(
    "ETH_RPC_URL",
    "http://host.docker.internal:8545"
)

CONTRACT_ADDRESS = os.getenv(
    "CONTRACT_ADDRESS",
    ""
)


web3 = Web3(
    Web3.HTTPProvider(
        ETH_RPC_URL
    )
)


def verify_payment(
    transaction_hash: str,
    wallet_address: str
):
    if not CONTRACT_ADDRESS:
        return {
            "success": False,
            "error": "CONTRACT_ADDRESS is not configured"
        }


    try:
        receipt = web3.eth.get_transaction_receipt(
            transaction_hash
        )

        transaction = web3.eth.get_transaction(
            transaction_hash
        )

    except Exception as error:
        return {
            "success": False,
            "error": str(error)
        }


    if receipt.status != 1:
        return {
            "success": False,
            "error": "Transaction failed"
        }


    if not transaction.to:
        return {
            "success": False,
            "error": "Transaction has no destination"
        }


    if (
        transaction.to.lower()
        != CONTRACT_ADDRESS.lower()
    ):
        return {
            "success": False,
            "error": "Wrong contract address"
        }


    if (
        transaction["from"].lower()
        != wallet_address.lower()
    ):
        return {
            "success": False,
            "error": "Wrong wallet address"
        }


    package_price = Web3.to_wei(
        0.002,
        "ether"
    )


    if transaction.value != package_price:
        return {
            "success": False,
            "error": "Wrong payment amount"
        }


    return {
        "success": True
    }