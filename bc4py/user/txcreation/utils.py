from bc4py.config import C, BlockChainError
from bc4py.database.builder import user_account
from bc4py.database.account import message2signature, create_new_user_keypair
from bc4py.database.tools import get_unspents_iter, get_utxo_iter
from bc4py.user import Balance
from logging import getLogger

log = getLogger('bc4py')

DUMMY_REDEEM_ADDRESS = '_____DUMMY______REDEEM______ADDRESS_____'  # 40letters


def fill_inputs_outputs(tx,
                        target_address=None,
                        cur=None,
                        signature_num=None,
                        fee_coin_id=0,
                        additional_gas=0,
                        dust_percent=0.8,
                        utxo_cashe=None):
    # outputsの合計を取得
    output_coins = Balance()
    for address, coin_id, amount in tx.outputs.copy():
        if address == DUMMY_REDEEM_ADDRESS:
            # 償還Outputは再構築するので消す
            tx.outputs.remove((address, coin_id, amount))
            continue
        output_coins[coin_id] += amount
    # 一時的にfeeの概算
    fee_coins = Balance(coin_id=fee_coin_id, amount=tx.gas_price * tx.gas_amount)
    # 必要なだけinputsを取得
    tx.inputs.clear()
    need_coins = output_coins + fee_coins
    input_coins = Balance()
    input_address = set()
    f_dust_skipped = False
    if utxo_cashe is None:
        if target_address:
            utxo_iter = get_utxo_iter(target_address=target_address)
        elif cur:
            utxo_iter = get_unspents_iter(outer_cur=cur)
        else:
            raise Exception('target_address and cur is None?')
        utxo_cashe = list()
        f_put_cashe = True
    else:
        utxo_iter = utxo_cashe
        f_put_cashe = False
    for address, height, txhash, txindex, coin_id, amount in utxo_iter:
        if f_put_cashe:
            utxo_cashe.append((address, height, txhash, txindex, coin_id, amount))
        if coin_id not in need_coins:
            continue
        elif need_coins[coin_id] * dust_percent > amount:
            f_dust_skipped = True
            continue
        need_coins[coin_id] -= amount
        input_coins[coin_id] += amount
        input_address.add(address)
        tx.inputs.append((txhash, txindex))
        if need_coins.is_all_minus_amount():
            break
    else:
        if f_dust_skipped and dust_percent > 0.00001:
            new_dust_percent = round(dust_percent * 0.7, 6)
            log.debug("Retry by lower dust percent. {}=>{}".format(dust_percent, new_dust_percent))
            return fill_inputs_outputs(
                tx=tx,
                target_address=target_address,
                cur=cur,
                signature_num=signature_num,
                fee_coin_id=fee_coin_id,
                additional_gas=additional_gas,
                dust_percent=new_dust_percent,
                utxo_cashe=utxo_cashe)
        elif len(tx.inputs) > 255:
            raise BlockChainError('Too many inputs, unspent tx\'s amount is too small.')
        else:
            raise BlockChainError('Insufficient balance. inputs={} needs={}'.format(input_coins, need_coins))
    # redeemを計算
    redeem_coins = input_coins - output_coins - fee_coins
    for coin_id, amount in redeem_coins:
        tx.outputs.append((DUMMY_REDEEM_ADDRESS, coin_id, amount))
    # Feeをチェックし再計算するか決める
    tx.serialize()
    if signature_num is None:
        need_gas_amount = tx.size + additional_gas + len(input_address) * C.SIGNATURE_GAS
    else:
        need_gas_amount = tx.size + additional_gas + signature_num * C.SIGNATURE_GAS
    if 0 <= tx.gas_amount - need_gas_amount < 10000:
        # input/outputを混ぜる
        return input_address
    else:
        # insufficient gas
        log.debug("Retry calculate tx fee. [{}=>{}+{}={}]".format(
            tx.gas_amount, tx.size + len(input_address) * C.SIGNATURE_GAS, additional_gas, need_gas_amount))
        tx.gas_amount = need_gas_amount
        return fill_inputs_outputs(
            tx=tx,
            target_address=target_address,
            cur=cur,
            signature_num=signature_num,
            fee_coin_id=fee_coin_id,
            additional_gas=additional_gas,
            dust_percent=dust_percent,
            utxo_cashe=utxo_cashe)


def replace_redeem_dummy_address(tx, cur=None, replace_by=None):
    assert cur or replace_by
    new_redeem_address = set()
    for index, (address, coin_id, amount) in enumerate(tx.outputs):
        if address != DUMMY_REDEEM_ADDRESS:
            continue
        if replace_by is None:
            new_address = create_new_user_keypair(user=C.ANT_UNKNOWN, cur=cur, is_inner=True)
        else:
            new_address = replace_by
        tx.outputs[index] = (new_address, coin_id, amount)
        new_redeem_address.add(new_address)
    tx.serialize()
    return new_redeem_address


def setup_signature(tx, input_address):
    # tx.signature.clear()
    count = 0
    for address in input_address:
        sign_pairs = message2signature(raw=tx.b, address=address)
        if sign_pairs not in tx.signature:
            tx.signature.append(sign_pairs)
            count += 1
    return count


def setup_contract_signature(tx, validators):
    count = 0
    for address in validators:
        try:
            sign_pairs = message2signature(raw=tx.b, address=address)
        except BlockChainError:
            continue
        if sign_pairs in tx.signature:
            pass
        elif sign_pairs:
            tx.signature.append(sign_pairs)
            count += 1
    return count


def check_enough_amount(sender, send_coins, fee_coins, cur):
    assert isinstance(sender, int)
    from_coins = user_account.get_balance(outer_cur=cur)[sender]
    remain_coins = from_coins - send_coins - fee_coins
    if not remain_coins.is_all_plus_amount():
        raise BlockChainError('Not enough balance in id={} balance={} remains={}.'.format(
            sender, from_coins, remain_coins))


__all__ = [
    "DUMMY_REDEEM_ADDRESS",
    "fill_inputs_outputs",
    "replace_redeem_dummy_address",
    "setup_signature",
    "setup_contract_signature",
    "check_enough_amount",
]
