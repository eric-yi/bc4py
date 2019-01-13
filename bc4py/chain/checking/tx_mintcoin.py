from bc4py.config import C, V, BlockChainError
from bc4py.chain.checking.signature import *
from bc4py.database.mintcoin import *
from bc4py.database.builder import tx_builder
from bc4py.user import Balance
import bjson


def check_tx_mint_coin(tx, include_block):
    if not (0 < len(tx.inputs) and 0 < len(tx.outputs)):
        raise BlockChainError('Input and output is more than 1.')
    elif tx.message_type != C.MSG_BYTE:
        raise BlockChainError('TX_MINT_COIN message is bytes.')
    elif include_block and 0 == include_block.txs.index(tx):
        raise BlockChainError('tx index is not proof tx.')
    elif tx.gas_amount < tx.size + len(tx.signature)*C.SIGNATURE_GAS + C.MINTCOIN_GAS:
        raise BlockChainError('Insufficient gas amount [{}<{}+{}+{}]'
                              .format(tx.gas_amount, tx.size, len(tx.signature)*C.SIGNATURE_GAS, C.MINTCOIN_GAS))
    # check new mintcoin format
    try:
        mint_id, params, setting = bjson.loads(tx.message)
    except Exception as e:
        raise BlockChainError('BjsonDecodeError: {}'.format(e))
    m_before = get_mintcoin_object(coin_id=mint_id, best_block=include_block, stop_txhash=tx.hash)
    result = check_mintcoin_new_format(m_before=m_before, new_params=params, new_setting=setting)
    if isinstance(result, str):
        raise BlockChainError('Failed check mintcoin block={}: {}'.format(include_block, result))
    # signature check
    require_cks, coins = input_output_digest(tx=tx)
    owner_address = m_before.address
    if owner_address:
        require_cks.add(owner_address)
    signed_cks = get_signed_cks(tx)
    if signed_cks != require_cks:
        raise BlockChainError('Signature check failed. signed={} require={} lack={}'
                              .format(signed_cks, require_cks, require_cks-signed_cks))
    # amount check
    include_coin_ids = set(coins.keys())  # include zero balance pair
    if include_coin_ids == {0, mint_id}:
        # increase/decrease mintcoin amount (exchange)
        # don't care about params and setting on this section
        if not m_before.setting['additional_issue']:
            raise BlockChainError('additional_issue is False but change amount.')
        if coins[0] + coins[mint_id] != 0:
            raise BlockChainError('46 Don\'t match input/output amount. {}'.format(coins))
        if coins[mint_id] < 0:
            pass  # increase
        if coins[mint_id] > 0:
            pass  # decrease
    elif len(include_coin_ids) == 1:
        include_id = include_coin_ids.pop()
        include_amount = coins[include_id]
        if include_id == 0:
            # only id=0, just only change mintcoin status
            if params is None and setting is None:
                raise BlockChainError('No update found.')
            if include_amount != 0:
                raise BlockChainError('59 Don\'t match input/output amount. {}'.format(coins))
        elif include_id == mint_id:
            raise BlockChainError('Only include mint_id, coins={}'.format(coins))
        else:
            raise BlockChainError('Unexpected include_id, {}'.format(include_id))
    else:
        raise BlockChainError('Unexpected include_coin_ids, {}'.format(include_coin_ids))


def input_output_digest(tx):
    require_cks = set()
    coins = Balance()
    # inputs
    for txhash, txindex in tx.inputs:
        input_tx = tx_builder.get_tx(txhash=txhash)
        if input_tx is None:
            raise BlockChainError('input tx is None. {}:{}'.format(txhash.hex(), txindex))
        address, coin_id, amount = input_tx.outputs[txindex]
        require_cks.add(address)
        coins[coin_id] += amount
    # outputs
    for address, coin_id, amount in tx.outputs:
        coins[coin_id] -= amount
    # fee
    coins[0] -= tx.gas_amount * tx.gas_price
    return require_cks, coins


__all__ = [
    "check_tx_mint_coin",
]
