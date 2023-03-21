import logging
from dataclasses import dataclass
from typing import List, Union

from eth.vm.forks.london.transactions import LondonTypedTransaction
from hexbytes import HexBytes
from starknet_py.contract import Contract
from starknet_py.net import AccountClient
from starknet_py.net.client_errors import ContractNotFoundError
from starknet_py.net.client_models import Call, Tag, TransactionStatus
from starknet_py.net.gateway_client import GatewayClient
from starknet_py.transaction_exceptions import TransactionNotReceivedError
from starkware.starknet.public.abi import get_selector_from_name

from ethjsonrpc.constants import (
    CHAIN_ID,
    GAS_PRICE,
    KAKAROT_ADDRESS,
    PRIORITY_GAS_PRICE,
)
from ethjsonrpc.utils import (
    get_account,
    get_eth_contract,
    get_explorer_url,
    get_kakarot_contract,
)

logging.basicConfig()
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


@dataclass
class EthClient:

    starknet_gateway: GatewayClient
    eth_contract: Contract
    kakarot_contract: Contract

    @staticmethod
    async def new(starknet_gateway_url: str):
        client = GatewayClient(net=starknet_gateway_url)
        eth_contract = await get_eth_contract(client)
        kakarot_contract = await get_kakarot_contract(client)
        return EthClient(client, eth_contract, kakarot_contract)

    async def compute_starknet_address(self, evm_address: str):
        return (
            await self.kakarot_contract.functions["compute_starknet_address"].call(
                int(evm_address, 16)
            )
        ).contract_address

    async def get_eoa(self, evm_address) -> AccountClient:
        starknet_address = await self.compute_starknet_address(evm_address)
        try:
            await self.starknet_gateway.get_code(starknet_address)
        except ContractNotFoundError:
            logger.info("ℹ️  EAO not deployed yet, deploying...")
            rpc_account = get_account()
            call = Call(
                to_addr=int(KAKAROT_ADDRESS, 16),
                selector=get_selector_from_name("deploy_externally_owned_account"),
                calldata=[int(evm_address, 16)],
            )
            tx_hash = (
                await rpc_account.execute(call, max_fee=int(1e16))
            ).transaction_hash
            logger.info(f"⏳ Waiting for tx {get_explorer_url('tx', tx_hash)}")
            await rpc_account.wait_for_tx(tx_hash)
        return get_account(starknet_address, "0xdead")

    def starknet_block_to_eth_block(self, block, transactions: bool):
        return {
            "baseFeePerGas": "0x1",
            "number": block.block_number
            if isinstance(block.block_number, int)
            else None,
            "hash": block.block_hash if isinstance(block.block_number, int) else None,
            "parentHash": block.parent_block_hash,
            "nonce": 0x0,  # DATA, 8 Bytes - hash of the generated proof-of-work. null when its pending block.
            "sha3Uncles": 0x0,  # DATA, 32 Bytes - SHA3 of the uncles data in the block.
            "logsBloom": None,  # DATA, 256 Bytes - the bloom filter for the logs of the block. null when its pending block.
            "transactionsRoot": 0x0,  # DATA, 32 Bytes - the root of the transaction trie of the block.
            "stateRoot": block.root,  # DATA, 32 Bytes - the root of the final state trie of the block.
            "receiptsRoot": 0x0,  # DATA, 32 Bytes - the root of the receipts trie of the block.
            "miner": f"0x{0:040x}",  # DATA, 20 Bytes - the address of the beneficiary to whom the mining rewards were given.
            "difficulty": 0x0,  # QUANTITY - integer of the difficulty for this block.
            "totalDifficulty": 0x0,  # QUANTITY - integer of the total difficulty of the chain until this block.
            "extraData": 0x0,  # DATA - the "extra data" field of this block.
            "size": 0x0,  # QUANTITY - integer the size of this block in bytes.
            "gasLimit": int(1e6),  # QUANTITY - the maximum gas allowed in this block.
            "gasUsed": 0x0,  # QUANTITY - the total used gas by all transactions in this block.
            "timestamp": 0x0,  # QUANTITY - the unix timestamp for when the block was collated.
            "transactions": [hex(t.hash) for t in block.transactions]
            if not transactions
            else block.transactions,  # Array - Array of transaction objects, or 32 Bytes transaction hashes depending on the last given parameter.
            "uncles": [],  # Array - Array of uncle hashes.
        }

    @staticmethod
    def is_legacy_tx(raw_tx: bytes):
        return raw_tx[0] > 0xC0

    @staticmethod
    def get_block_number(block_number: str) -> Union[Tag, int]:
        if block_number.startswith("0x"):
            return int(block_number, 16)
        return block_number

    async def net_version(self) -> str:
        return hex(CHAIN_ID)

    async def eth_chainId(self) -> str:
        return hex(CHAIN_ID)

    async def eth_gasPrice(self) -> str:
        return hex(GAS_PRICE)

    async def eth_maxPriorityFeePerGas(self) -> str:
        return hex(PRIORITY_GAS_PRICE)

    async def eth_feeHistory(
        self, block_count: str, block_number: str, percentiles: List[int]
    ):
        block = await self.starknet_gateway.get_block(
            block_number=self.get_block_number(block_number)
        )
        block_count = int(block_count, 16)
        return {
            "oldestBlock": hex(block.block_number - block_count),
            "reward": [[hex(int(1e7))] * len(percentiles) for _ in range(block_count)],
            "baseFeePerGas": [hex(int(1e9))] * (block.block_number + 1),
            "gasUsedRatio": [0.5] * block_count,
        }

    async def eth_blockNumber(self) -> str:
        return hex(
            (await self.starknet_gateway.get_block(block_number="latest")).block_number
        )

    async def eth_getBalance(self, evm_address, block_number) -> str:
        starknet_address = await self.compute_starknet_address(evm_address)

        block_hash = (
            await self.starknet_gateway.get_block(block_number=int(block_number, 16))
        ).block_hash
        return hex(
            (
                await self.eth_contract.functions["balanceOf"].call(
                    starknet_address, block_hash=hex(block_hash)
                )
            ).balance
        )

    async def eth_getTransactionCount(self, evm_address, block_number) -> str:
        eoa = await self.get_eoa(evm_address)
        try:
            block_number = int(block_number, 16)
        except ValueError:
            pass
        block_hash = (
            await self.starknet_gateway.get_block(block_number=block_number)
        ).block_hash
        nonce = await self.starknet_gateway.get_contract_nonce(
            eoa.address, block_hash=block_hash
        )
        return hex(nonce)

    async def eth_sendRawTransaction(self, raw_tx: str) -> str:
        tx = HexBytes(raw_tx)
        is_legacy = self.is_legacy_tx(tx)
        if is_legacy:
            raise ValueError("Cannot decode legacy tx")
        sender = LondonTypedTransaction.decode(tx).get_sender().hex()
        eoa = await self.get_eoa(f"0x{sender}")
        call = Call(
            to_addr=0xDEAD,
            selector=0xDEAD,
            calldata=list(tx),
        )
        receipt = await eoa.execute(call, max_fee=int(1e18))
        return f"0x{receipt.transaction_hash:064x}"

    async def eth_call(self, tx, block_number) -> str:
        if "to" not in tx:
            # Currently not possible to call for a deploy tx
            return hex(int(1e18))
        else:
            block_hash = (
                await self.starknet_gateway.get_block(
                    block_number=int(block_number, 16)
                )
            ).block_hash
            return "".join(
                (
                    await self.kakarot_contract.functions["execute_at_address"]
                    .prepare(
                        int(tx["to"], 16),
                        int(tx.get("value", "0x0"), 16),
                        int(tx["gas"], 16),
                        HexBytes(tx["data"]),
                    )
                    .call(block_hash=hex(block_hash))
                ).as_tuple()
            )

    async def eth_estimateGas(self, tx) -> str:
        return hex(21_000)

    async def eth_getBlockByHash(self, block_hash: str, transactions: bool) -> dict:
        block = await self.starknet_gateway.get_block(block_hash=block_hash)
        return self.starknet_block_to_eth_block(block, transactions)

    async def eth_getBlockByNumber(self, block_number: str, transactions: bool) -> dict:
        if not (block_number == "latest" or block_number == "pending"):
            block_number = int(block_number, 16)
        block = await self.starknet_gateway.get_block(block_number=block_number)
        return self.starknet_block_to_eth_block(block, transactions)

    async def eth_getTransactionReceipt(self, tx_hash):
        receipt = await self.starknet_gateway.get_transaction_receipt(tx_hash)
        try:
            tx = await self.starknet_gateway.get_transaction(tx_hash)
            call = Call(
                to_addr=tx.contract_address,
                selector=get_selector_from_name("get_evm_address"),
                calldata=[],
            )
            sender = hex((await self.starknet_gateway.call_contract(call))[0])
        except TransactionNotReceivedError:
            sender = f"0x{0:040}"
            pass
        return {
            "transactionHash": tx_hash,
            "blockHash": hex(receipt.block_hash or 0),
            "blockNumber": hex(receipt.block_number or 0),
            "logs": [],
            "contractAddress": None,
            "effectiveGasPrice": receipt.actual_fee,
            "cumulativeGasUsed": "0xbe8cde",
            "from": sender,
            "gasUsed": "0x565f",
            "logsBloom": "0x00000000000000000000000000000000000100004000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000008000000000000000000000000000000000000000000000000000000000000000000000000000000000000200000000000000000000000000000000000000000000000000000000000000080000000000000000000000000000000000000000000000000000000000000000000000000800000000000000000000000000000000000000000000000000000000000",
            "status": hex(
                int(
                    receipt.status
                    in [
                        TransactionStatus.ACCEPTED_ON_L1,
                        TransactionStatus.ACCEPTED_ON_L2,
                        TransactionStatus.PENDING,
                    ]
                )
            ),
            "to": None,
            "transactionIndex": "0x1",
            "type": "0x2",
        }

    async def eth_getCode(self, evm_address, block_number):
        starknet_address = await self.compute_starknet_address(evm_address)
        try:
            return await self.starknet_gateway.get_code(
                starknet_address, block_number=self.get_block_number(block_number)
            )
        except ContractNotFoundError:
            return "0x0"

    async def eth_getTransactionByHash(self, tx_hash):
        tx = await self.starknet_gateway.get_transaction(tx_hash)
        call = Call(
            to_addr=tx.contract_address,
            selector=get_selector_from_name("get_evm_address"),
            calldata=[],
        )
        sender = hex((await self.starknet_gateway.call_contract(call))[0])
        receipt = await self.starknet_gateway.get_transaction_receipt(tx_hash)
        return {
            "blockHash": hex(receipt.block_hash or 0),
            "blockNumber": hex(receipt.block_number or 0),
            "from": sender,
            "gas": "0xc350",
            "gasPrice": "0x4a817c800",
            "hash": "0x88df016429689c079f3b2f6ad39fa052532c56795b733da78a91ebe6a713944b",
            "input": "0x68656c6c6f21",
            "nonce": "0x15",
            "to": "0xf02c1c8e6114b1dbe8937a39260b5b0a374432bb",
            "transactionIndex": "0x41",
            "value": "0xf3dbb76162000",
            "v": "0x25",
            "r": "0x1b5e176d927f8e9ab405058b2d2457392da3e20f328b16ddabcebc33eaac5fea",
            "s": "0x4ba69724e8f69de52f0125ad8b3c5c2cef33019bac3249e2c0a2192766d1721c",
        }
