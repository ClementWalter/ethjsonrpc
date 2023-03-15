# ethjsonrpc

Python client for Kakarot using the JSON-RPC interface

- complete: implements all 62 JSON-RPC methods plus several client-specific methods
- provides a high-level interface to create contracts on the blockchain and to call contract methods

## Important note

The API is not yet stable, so please use caution when upgrading.

## Implemented JSON-RPC methods

- web3_clientVersion
- web3_sha3
- net_version
- net_listening
- net_peerCount
- eth_protocolVersion
- eth_syncing
- eth_coinbase
- eth_mining
- eth_hashrate
- eth_gasPrice
- eth_accounts
- eth_blockNumber
- eth_getBalance
- eth_getStorageAt
- eth_getTransactionCount
- eth_getBlockTransactionCountByHash
- eth_getBlockTransactionCountByNumber
- eth_getUncleCountByBlockHash
- eth_getUncleCountByBlockNumber
- eth_getCode
- eth_sign
- eth_sendTransaction
- eth_sendRawTransaction
- eth_call
- eth_estimateGas
- eth_getBlockByHash
- eth_getBlockByNumber
- eth_getTransactionByHash
- eth_getTransactionByBlockHashAndIndex
- eth_getTransactionByBlockNumberAndIndex
- eth_getTransactionReceipt
- eth_getUncleByBlockHashAndIndex
- eth_getUncleByBlockNumberAndIndex
- eth_getCompilers
- eth_compileSolidity
- eth_compileLLL
- eth_compileSerpent
- eth_newFilter
- eth_newBlockFilter
- eth_newPendingTransactionFilter
- eth_uninstallFilter
- eth_getFilterChanges
- eth_getFilterLogs
- eth_getLogs
- eth_getWork
- eth_submitWork
- eth_submitHashrate
- db_putString
- db_getString
- db_putHex
- db_getHex
- shh_version
- shh_post
- shh_newIdentity
- shh_hasIdentity
- shh_newGroup
- shh_addToGroup
- shh_newFilter
- shh_uninstallFilter
- shh_getFilterChanges
- shh_getMessages

## Reference

- [JSON-RPC wiki](https://github.com/ethereum/wiki/wiki/JSON-RPC)
