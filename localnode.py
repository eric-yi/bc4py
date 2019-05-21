#!/user/env python3
# -*- coding: utf-8 -*-

from bc4py import __version__, __chain_version__, __message__, __logo__
from bc4py.config import C, V, P
from bc4py.utils import set_database_path, set_blockchain_params, check_already_started
# from bc4py.user.stratum import Stratum, start_stratum, close_stratum
from bc4py.user.generate import *
from bc4py.user.boot import *
from bc4py.user.network import *
from bc4py.user.api import create_rest_server
from bc4py.contract.emulator import start_emulators, Emulate
from bc4py.database.create import check_account_db
from bc4py.database.builder import chain_builder
from bc4py.chain.msgpack import default_hook, object_hook
from p2p_python.utils import setup_p2p_params
from p2p_python.client import PeerClient
from bc4py.for_debug import set_logger, f_already_bind
from threading import Thread
import logging
import os


def copy_boot(port):
    if port == 2000:
        return
    else:
        original = os.path.join(os.path.split(V.DB_HOME_DIR)[0], '2000', 'boot.json')
    destination = os.path.join(V.DB_HOME_DIR, 'boot.json')
    if original == destination:
        return
    with open(original, mode='br') as ifp:
        with open(destination, mode='bw') as ofp:
            ofp.write(ifp.read())


def work(port, sub_dir):
    # BlockChain setup
    set_database_path(sub_dir=sub_dir)
    check_already_started()
    chain_builder.set_database_path()
    copy_boot(port)
    import_keystone(passphrase='hello python')
    check_account_db()
    genesis_block, genesis_params, network_ver, connections = load_boot_file()
    logging.info("Start p2p network-ver{} .".format(network_ver))

    # P2P network setup
    setup_p2p_params(network_ver=network_ver, p2p_port=port, sub_dir=sub_dir)
    pc = PeerClient(f_local=True, default_hook=default_hook, object_hook=object_hook)
    pc.event.addevent(cmd=DirectCmd.BEST_INFO, f=DirectCmd.best_info)
    pc.event.addevent(cmd=DirectCmd.BLOCK_BY_HEIGHT, f=DirectCmd.block_by_height)
    pc.event.addevent(cmd=DirectCmd.BLOCK_BY_HASH, f=DirectCmd.block_by_hash)
    pc.event.addevent(cmd=DirectCmd.TX_BY_HASH, f=DirectCmd.tx_by_hash)
    pc.event.addevent(cmd=DirectCmd.UNCONFIRMED_TX, f=DirectCmd.unconfirmed_tx)
    pc.event.addevent(cmd=DirectCmd.BIG_BLOCKS, f=DirectCmd.big_blocks)
    pc.start()
    V.PC_OBJ = pc

    # for debug node
    if port != 2000 and pc.p2p.create_connection('127.0.0.1', 2000):
        logging.info("Connect!")
    else:
        pc.p2p.create_connection('127.0.0.1', 2001)

    for host, port in connections:
        pc.p2p.create_connection(host, port)
    set_blockchain_params(genesis_block, genesis_params)

    # BroadcastProcess setup
    pc.broadcast_check = broadcast_check

    # Update to newest blockchain
    chain_builder.db.sync = False
    if chain_builder.init(genesis_block, batch_size=500):
        # only genesisBlock yoy have, try to import bootstrap.dat.gz
        load_bootstrap_file()
    sync_chain_loop()

    # Mining/Staking setup
    # Debug.F_CONSTANT_DIFF = True
    # Debug.F_SHOW_DIFFICULTY = True
    # Debug.F_STICKY_TX_REJECTION = False  # for debug
    if port == 2000:
        Generate(consensus=C.BLOCK_CAP_POS, power_limit=0.6, path='E:\\plots').start()
    elif port % 3 == 0:
        Generate(consensus=C.BLOCK_YES_POW, power_limit=0.03).start()
    elif port % 3 == 1:
        Generate(consensus=C.BLOCK_X16S_POW, power_limit=0.03).start()
    elif port % 3 == 2:
        Generate(consensus=C.BLOCK_X11_POW, power_limit=0.03).start()
    Generate(consensus=C.BLOCK_COIN_POS, power_limit=0.3).start()
    # contract emulator
    Emulate(c_address='CJ4QZ7FDEH5J7B2O3OLPASBHAFEDP6I7UKI2YMKF')
    # Emulate(c_address='CLBKXHOTXTLK3FENVTCH6YPM5MFZS4BNAXFYNWBD')
    start_emulators()
    # Stratum
    # Stratum(port=port+2000, consensus=C.BLOCK_HMQ_POW, first_difficulty=4)
    Thread(target=mined_newblock, name='GeneBlock', args=(output_que,)).start()
    logging.info("Finished all initialize.")

    try:
        # start_stratum(f_blocking=False)
        create_rest_server(user='user', pwd='password', port=port+1000)
        P.F_STOP = True
        chain_builder.close()
        # close_stratum()
        pc.close()
    except KeyboardInterrupt:
        logging.debug("KeyboardInterrupt.")


def connection():
    port = 2000
    while True:
        if f_already_bind(port):
            port += 1
            continue
        path = 'debug.2000.log' if port == 2000 else None
        set_logger(level=logging.DEBUG, path=path, f_remove=True)
        logging.info("\n{}\n=====\n{}, chain-ver={}\n{}\n"
                     .format(__logo__, __version__, __chain_version__, __message__))
        work(port=port, sub_dir=str(port))
        break


if __name__ == '__main__':
    connection()
