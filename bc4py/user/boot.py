from bc4py.config import C, V
from bc4py.chain.block import Block
from bc4py.chain.tx import TX
from bc4py.utils import AESCipher
from bc4py.database.create import closing, create_db
from bc4py.database.builder import builder, tx_builder
from bc4py.chain.checking import new_insert_block
import os
import bjson
import pickle
import random
from base64 import b64decode, b64encode
from mnemonic import Mnemonic
from bip32nem import BIP32Key, BIP32_HARDEN
from threading import Thread
from time import sleep
import json
from logging import getLogger

log = getLogger('bc4py')


def create_boot_file(genesis_block, network_ver=None, connections=None):
    network_ver = network_ver or random.randint(1000000, 0xffffffff)
    assert isinstance(network_ver, int) and abs(network_ver) <= 0xffffffff, 'network_ver is int <=0xffffffff.'
    data = {
        'block': genesis_block.b,
        'txs': [tx.b for tx in genesis_block.txs],
        'connections': connections or list(),
        'network_ver': network_ver}
    boot_path = os.path.join(V.DB_HOME_DIR, 'boot.dat')
    data = b64encode(bjson.dumps(data))
    with open(boot_path, mode='bw') as fp:
        while len(data) > 0:
            write, data = data[:60], data[60:]
            fp.write(write+b'\n')
    log.info("create new boot.dat!")


def load_boot_file():
    normal_path = os.path.join(os.path.abspath(os.path.dirname(__file__)), 'boot.dat')
    extra_path = os.path.join(V.DB_HOME_DIR, 'boot.dat')
    if os.path.exists(normal_path):
        with open(normal_path, mode='br') as fp:
            data = bjson.loads(b64decode(fp.read().replace(b'\n', b'').replace(b'\r', b'')))
    elif os.path.exists(extra_path):
        with open(extra_path, mode='br') as fp:
            data = bjson.loads(b64decode(fp.read().replace(b'\n', b'').replace(b'\r', b'')))
    else:
        raise FileNotFoundError('Cannot find boot.dat "{}" or "{}" ?'.format(normal_path, extra_path))
    genesis_block = Block.from_binary(binary=data['block'])
    genesis_block.flag = C.BLOCK_GENESIS
    genesis_block.height = 0
    for b_tx in data['txs']:
        tx = TX.from_binary(binary=b_tx)
        tx.height = 0
        genesis_block.txs.append(tx)
    connections = data.get('connections', list())
    network_ver = data['network_ver']
    return genesis_block, network_ver, connections


def create_bootstrap_file():
    boot_path = os.path.join(V.DB_HOME_DIR, 'bootstrap.dat')
    with open(boot_path, mode='ba') as fp:
        for height, blockhash in builder.db.read_block_hash_iter(start_height=0):
            block = builder.db.read_block(blockhash)
            fp.write(b64encode(pickle.dumps(block))+b'\n')
    log.info("create new bootstrap.dat!")


def load_bootstrap_file():
    boot_path = os.path.join(V.DB_HOME_DIR, 'bootstrap.dat')
    with open(boot_path, mode='br') as fp:
        b_data = fp.readline()
        block = None
        while b_data:
            block = pickle.loads(b64decode(b_data.rstrip()))
            for tx in block.txs:
                tx.height = None
                if tx.type in (C.TX_POW_REWARD, C.TX_POS_REWARD):
                    continue
                tx_builder.put_unconfirmed(tx)
            for tx in block.txs:
                tx.height = block.height
            new_insert_block(block=block, time_check=False)
            b_data = fp.readline()
    log.debug("load bootstrap.dat! last={}".format(block))


def import_keystone(passphrase='', auto_create=True, language='english'):
    def timeout_now(count):
        while count > 0:
            count -= 1
            sleep(1)
        V.BIP44_BRANCH_SEC_KEY = None
        log.info("deleted wallet secret key now.")
    if V.BIP44_ENCRYPTED_MNEMONIC:
        raise Exception('Already imported, BIP32_ENCRYPTED_MNEMONIC.')
    if V.BIP44_ROOT_PUB_KEY:
        raise Exception('Already imported, BIP32_ROOT_PUBLIC_KEY.')
    keystone_path = os.path.join(V.DB_HOME_DIR, 'keystone.json')
    old_account_path = os.path.join(V.DB_HOME_DIR, 'account.dat')
    if os.path.exists(keystone_path):
        # import from keystone file
        mnemonic, bip, pub, timeout = load_keystone(keystone_path)
    elif os.path.exists(old_account_path):
        # create keystone and swap old account format
        if not os.path.exists(V.DB_ACCOUNT_PATH):
            raise Exception('wallet.dat is not created yet.')
        mnemonic, bip, pub, timeout = create_keystone(passphrase, keystone_path, language)
        with closing(create_db(old_account_path)) as old_db:
            old_cur = old_db.cursor()
            with closing(create_db(V.DB_ACCOUNT_PATH)) as new_db:
                new_cur = new_db.cursor()
                swap_old_format(old_cur=old_cur, new_cur=new_cur, bip=bip)
                new_db.commit()
        os.rename(src=old_account_path, dst=old_account_path+'.old')
    else:
        if not auto_create:
            raise Exception('Cannot load wallet info from {}'.format(keystone_path))
        mnemonic, bip, pub, timeout = create_keystone(passphrase, keystone_path, language)
    V.BIP44_ENCRYPTED_MNEMONIC = mnemonic
    V.BIP44_ROOT_PUB_KEY = pub
    if bip:
        # m/44' / coin_type' / account' / change / address_index
        V.BIP44_BRANCH_SEC_KEY = bip \
            .ChildKey(44 + BIP32_HARDEN) \
            .ChildKey(C.BIP44_COIN_TYPE) \
            .ExtendedKey(private=True)
    if timeout > 0:
        Thread(target=timeout_now, args=(timeout,), name='timer{}Sec'.format(timeout)).start()
    log.info("import wallet, unlock={} timeout={}".format(bool(bip), timeout))


def swap_old_format(old_cur, new_cur, bip):
    secret_key = bip \
        .ChildKey(44 + BIP32_HARDEN) \
        .ChildKey(C.BIP44_COIN_TYPE) \
        .ExtendedKey(private=True)
    secret_key = secret_key.encode()
    for uuid, sk, pk, ck, user, time in old_cur.execute("SELECT * FROM `pool`"):
        sk = AESCipher.encrypt(key=secret_key, raw=sk)
        new_cur.execute("INSERT OR IGNORE INTO `pool` (`id`,`sk`,`ck`,`user`,`time`) VALUES (?,?,?,?,?)", (
            uuid, sk, ck, user, time))
    for args in old_cur.execute("SELECT * FROM `log`"):
        new_cur.execute("INSERT OR IGNORE INTO `log` VALUES (?,?,?,?,?,?,?,?)", args)
    for args in old_cur.execute("SELECT * FROM `account`"):
        new_cur.execute("INSERT OR IGNORE INTO `account` VALUES (?,?,?,?)", args)


def load_keystone(keystone_path):
    with open(keystone_path, mode='r') as fp:
        wallet = json.load(fp)
    pub = str(wallet['public_key'])
    mnemonic = str(wallet['mnemonic'])
    if 'passphrase' in wallet:
        passphrase = str(wallet['passphrase'])
        timeout = int(wallet.get('timeout', -1))
        seed = Mnemonic.to_seed(mnemonic, passphrase)
        bip = BIP32Key.fromEntropy(entropy=seed)
        if pub != bip.ExtendedKey(private=False):
            raise Exception('Don\'t match with public key.')
    else:
        bip = None
        timeout = -1
    return mnemonic, bip, pub, timeout


def create_keystone(passphrase, keystone_path, language='english'):
    mnemonic = Mnemonic(language).generate()
    seed = Mnemonic.to_seed(mnemonic, passphrase)
    bip = BIP32Key.fromEntropy(seed)
    pub = bip.ExtendedKey(private=False)
    timeout = -1
    wallet = {
        'private_key': bip.ExtendedKey(private=True),
        'public_key': pub,
        'mnemonic': mnemonic,
        'passphrase': passphrase,
        'timeout': timeout,
        'comments': 'You should remove "private_key" and "passphrase" for security.'
                    'Please don\'t forget the two key\'s value or lost your coins.'
                    'timeout\'s value "-1" make system auto deletion disable.'}
    with open(keystone_path, mode='w') as fp:
        json.dump(wallet, fp, indent=4)
    return mnemonic, bip, pub, timeout


__all__ = [
    "create_boot_file",
    "load_boot_file",
    "create_bootstrap_file",
    "load_bootstrap_file",
    "import_keystone"
]
