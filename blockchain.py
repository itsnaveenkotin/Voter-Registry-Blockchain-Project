from web3 import Web3
from eth_account import Account
import json
import os

class Blockchain:
    def __init__(self):
        # Connect to local Ganache instance
        self.w3 = Web3(Web3.HTTPProvider('http://127.0.0.1:7545'))
        
        # Load contract ABI and address
        contract_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'build/contracts/VoterRegistry.json')
        with open(contract_path) as f:
            contract_json = json.load(f)
            self.contract_abi = contract_json['abi']
            # Get the latest deployed contract address
            self.contract_address = self.w3.to_checksum_address(contract_json['networks'][list(contract_json['networks'].keys())[-1]]['address'])
        
        # Create contract instance
        self.contract = self.w3.eth.contract(address=self.contract_address, abi=self.contract_abi)
    
    def create_ethereum_account(self):
        account = Account.create()
        return account.address, account.key.hex()
    
    def register_voter(self, voter_id, eth_address):
        # Get the first account from Ganache as admin
        admin_account = self.w3.eth.accounts[0]
        
        # Build the transaction
        transaction = self.contract.functions.registerVoter(
            Web3.keccak(text=voter_id),
            eth_address
        ).build_transaction({
            'from': admin_account,
            'gas': 2000000,
            'gasPrice': self.w3.eth.gas_price,
            'nonce': self.w3.eth.get_transaction_count(admin_account),
        })
        
        # Sign and send the transaction
        signed_txn = self.w3.eth.account.sign_transaction(transaction, private_key=os.environ.get('ADMIN_PRIVATE_KEY'))
        tx_hash = self.w3.eth.send_raw_transaction(signed_txn.rawTransaction)
        
        # Wait for transaction receipt
        tx_receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash)
        return tx_receipt