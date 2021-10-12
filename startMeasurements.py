import json
import time
import os

from dotenv import load_dotenv
from eth_account import Account
from web3.auto import w3
from sensorhub_master.sensorhub.hub import SensorHub


class EnvironmentManager:
    def __init__(self):
        load_dotenv()

    def getenv_or_raise(self, key):
        value = os.getenv(key)
        if value is None:
            raise Exception(f'{key} variable not found in .env')
        return value


class AccountManager:
    def __init__(self, private_key, address):
        self.private_key = private_key
        self.address = address

    def sign_transaction(self, transaction):
        signed = Account.sign_transaction(transaction_dict=transaction, private_key=self.private_key)
        return signed.rawTransaction

    def send_signed_tx(self, func, value, time):
        nonce = w3.eth.getTransactionCount(self.address)
        raw_tx = func(value, time).buildTransaction({'nonce': nonce, 'gasPrice': 0, 'gas': 300000, 'from': self.address})
        signed_tx = self.sign_transaction(raw_tx)
        hash_tx = w3.eth.send_raw_transaction(signed_tx)
        w3.eth.wait_for_transaction_receipt(hash_tx.hex())
        return hash_tx.hex()


class ContractManager:
    def __init__(self, account_manager):
        with open('./Contract/SimpleTemp.abi') as fabi:
            with open('./Contract/address.txt') as faddr:
                abi = json.load(fabi)
                contract_address = faddr.read()
                self.contract = w3.eth.contract(address=contract_address, abi=abi)
                self.account_manager = account_manager

    def get_contract(self):
        return self.contract

    def get_measurements_func(self):
        return self.contract.get_function_by_name('getMeasurements')

    def store_measurement_func(self):
        return self.contract.get_function_by_name('storeMeasurement')

    def print_measurements(self):
        print(self.get_measurements_func().call())

    def store_measurement(self, value, time):
        store_func = self.store_measurement_func()
        hash_tx = self.account_manager.send_signed_tx(store_func, value, time)
        print("Measurement stored -> hash: ", hash_tx)


if not w3.isConnected():
    raise Exception(f'Cannot connect to web3')

env_manager = EnvironmentManager()
private_key = env_manager.getenv_or_raise('SIGNER_LOCAL_PRIVATE_KEY')
address = env_manager.getenv_or_raise('SIGNER_LOCAL_ADDRESS')
_account_manager = AccountManager(private_key=private_key, address=address)
contract_manager = ContractManager(_account_manager)
hub = SensorHub()

n=0
while n<100:
    n += 1
    temp = hub.get_off_board_temperature()
    now = int(time.time())
    print('temp: ', temp, 'time: ', now)
    contract_manager.store_measurement(temp, now)
    time.sleep(1)

contract_manager.print_measurements()