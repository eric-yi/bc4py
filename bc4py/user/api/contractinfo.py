from bc4py.config import C, P
from bc4py.user.api import utils
from bc4py.database.builder import chain_builder, tx_builder
from bc4py.database.validator import get_validator_object, validator_tx2index
from bc4py.database.contract import get_contract_object, start_tx2index
from bc4py.contract.emulator.watching import watching_tx
from binascii import a2b_hex
import pickle
from base64 import b64encode
from logging import getLogger

log = getLogger('bc4py')


async def contract_info(request):
    try:
        c_address = request.query['c_address']
        f_confirmed = bool(request.query.get('confirmed', False))
        stop_hash = request.query.get('stophash', None)
        if stop_hash:
            stop_hash = a2b_hex(stop_hash)
        best_block = chain_builder.best_block if f_confirmed else None
        c = get_contract_object(c_address=c_address, best_block=best_block, stop_txhash=stop_hash)
        return utils.json_res(c.info)
    except Exception as e:
        log.error(e)
        return utils.error_res()


async def validator_info(request):
    try:
        v_address = request.query['v_address']
        f_confirmed = bool(request.query.get('confirmed', False))
        stop_hash = request.query.get('stophash', None)
        if stop_hash:
            stop_hash = a2b_hex(stop_hash)
        best_block = chain_builder.best_block if f_confirmed else None
        v = get_validator_object(v_address=v_address, best_block=best_block, stop_txhash=stop_hash)
        return utils.json_res(v.info)
    except Exception as e:
        log.error(e)
        return utils.error_res()


async def get_contract_history(request):
    try:
        c_address = request.query['c_address']
        data = list()
        # database
        for index, start_hash, finish_hash, (c_method, c_args, c_storage) in\
                chain_builder.db.read_contract_iter(c_address=c_address):
            data.append({
                'index': index,
                'height': index // 0xffffffff,
                'status': 'database',
                'start_hash': start_hash.hex(),
                'finish_hash': finish_hash.hex(),
                'c_method': c_method,
                'c_args': [decode(a) for a in c_args],
                'c_storage': {decode(k): decode(v) for k, v in c_storage.items()} if c_storage else None
            })
        # memory
        for block in reversed(chain_builder.best_chain):
            for tx in block.txs:
                if tx.type != C.TX_CONCLUDE_CONTRACT:
                    continue
                _c_address, start_hash, c_storage = tx.encoded_message()
                if _c_address != c_address:
                    continue
                start_tx = tx_builder.get_tx(txhash=start_hash)
                dummy, c_method, redeem_address, c_args = start_tx.encoded_message()
                index = start_tx2index(start_tx=start_tx)
                data.append({
                    'index': index,
                    'height': tx.height,
                    'status': 'memory',
                    'start_hash': start_hash.hex(),
                    'finish_hash': tx.hash.hex(),
                    'c_method': c_method,
                    'c_args': [decode(a) for a in c_args],
                    'c_storage': {decode(k): decode(v) for k, v in c_storage.items()} if c_storage else None,
                })
        # unconfirmed
        for tx in sorted(tx_builder.unconfirmed.values(), key=lambda x: x.create_time):
            if tx.type != C.TX_CONCLUDE_CONTRACT:
                continue
            _c_address, start_hash, c_storage = tx.encoded_message()
            if _c_address != c_address:
                continue
            start_tx = tx_builder.get_tx(txhash=start_hash)
            dummy, c_method, redeem_address, c_args = start_tx.encoded_message()
            index = start_tx2index(start_tx=start_tx)
            data.append({
                'index': index,
                'height': tx.height,
                'status': 'unconfirmed',
                'start_hash': start_hash.hex(),
                'finish_hash': tx.hash.hex(),
                'c_method': c_method,
                'c_args': [decode(a) for a in c_args],
                'c_storage': {decode(k): decode(v) for k, v in c_storage.items()} if c_storage else None,
            })
        return utils.json_res(data)
    except Exception as e:
        log.error(e)
        return utils.error_res()


async def get_validator_history(request):
    try:
        v_address = request.query['v_address']
        data = list()
        # database
        for index, new_address, flag, txhash, sig_diff in chain_builder.db.read_validator_iter(v_address=v_address):
            data.append({
                'index': index,
                'height': index // 0xffffffff,
                'new_address': new_address,
                'flag': flag,
                'txhash': txhash.hex(),
                'sig_diff': sig_diff
            })
        # memory
        for block in reversed(chain_builder.best_chain):
            for tx in block.txs:
                if tx.type != C.TX_VALIDATOR_EDIT:
                    continue
                _c_address, new_address, flag, sig_diff = tx.encoded_message()
                if _c_address != v_address:
                    continue
                index = validator_tx2index(tx=tx)
                data.append({
                    'index': index,
                    'height': tx.height,
                    'new_address': new_address,
                    'flag': flag,
                    'txhash': tx.hash.hex(),
                    'sig_diff': sig_diff
                })
        # unconfirmed
        for tx in sorted(tx_builder.unconfirmed.values(), key=lambda x: x.create_time):
            if tx.type != C.TX_VALIDATOR_EDIT:
                continue
            _c_address, new_address, flag, sig_diff = tx.encoded_message()
            if _c_address != v_address:
                continue
            data.append({
                'index': None,
                'height': None,
                'new_address': new_address,
                'flag': flag,
                'txhash': tx.hash.hex(),
                'sig_diff': sig_diff
            })
        return utils.json_res(data)
    except Exception as e:
        log.error(e)
        return utils.error_res()


async def contract_storage(request):
    try:
        c_address = request.query['c_address']
        f_confirmed = bool(request.query.get('confirmed', False))
        stop_hash = request.query.get('stophash', None)
        if stop_hash:
            stop_hash = a2b_hex(stop_hash)
        f_pickle = bool(request.query.get('pickle', False))
        best_block = chain_builder.best_block if f_confirmed else None
        c = get_contract_object(c_address=c_address, best_block=best_block, stop_txhash=stop_hash)
        if c is None:
            return utils.json_res({})
        elif f_pickle:
            storage = b64encode(pickle.dumps(c.storage)).decode()
        else:
            storage = {decode(k): decode(v) for k, v in c.storage.items()}
        return utils.json_res(storage)
    except Exception as e:
        log.error(e)
        return utils.error_res()


async def watching_info(request):
    try:
        # You need to enable watching option!
        return utils.json_res([{
            'hash': txhash.hex(),
            'type': tx.type,
            'tx': str(tx),
            'time': time,
            'c_address': c_address,
            'related': related_list,
            'args': tuple(map(decode, args)),
        } for txhash, (time, tx, related_list, c_address, *args) in watching_tx.items()])
    except Exception as e:
        log.error(e)
        return utils.error_res()


def decode(b):
    if isinstance(b, bytes) or isinstance(b, bytearray):
        return b.hex()
    elif isinstance(b, set) or isinstance(b, list) or isinstance(b, tuple):
        return tuple(decode(data) for data in b)
    elif isinstance(b, dict):
        return {decode(k): decode(v) for k, v in b.items()}
    else:
        return b
        # return 'Cannot decode type {}'.format(type(b))


__all__ = [
    "contract_info",
    "validator_info",
    "get_contract_history",
    "get_validator_history",
    "contract_storage",
    "watching_info",
]
