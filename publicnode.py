#!/user/env python3
# -*- coding: utf-8 -*-

from bc4py import __version__, __chain_version__, __block_version__, __message__, __logo__
from bc4py.config import C, V
from bc4py.utils import *
from bc4py.exit import blocking_run
from bc4py.user.generate import *
from bc4py.user.boot import *
from bc4py.user.network import *
from bc4py.user.api import setup_rest_server
from bc4py.database.create import check_account_db
from bc4py.database.builder import chain_builder
from bc4py.chain.msgpack import default_hook, object_hook
from p2p_python.utils import setup_p2p_params
from p2p_python.server import Peer2Peer
from bc4py.for_debug import set_logger
import asyncio
import logging


loop = asyncio.get_event_loop()


def setup_client(p2p_port, sub_dir=None):
    # BlockChain setup
    set_database_path(sub_dir=sub_dir)
    check_already_started()
    chain_builder.set_database_object()
    import_keystone(passphrase='hello python')
    loop.run_until_complete(check_account_db())
    genesis_block, genesis_params, network_ver, connections = load_boot_file()
    set_blockchain_params(genesis_block, genesis_params)
    logging.info("Start p2p network-ver{} .".format(network_ver))

    # P2P network setup
    setup_p2p_params(network_ver=network_ver, p2p_port=p2p_port, sub_dir=sub_dir)
    p2p = Peer2Peer(default_hook=default_hook, object_hook=object_hook)
    p2p.event.setup_events_from_class(DirectCmd)
    p2p.setup()
    V.P2P_OBJ = p2p
    return connections


async def setup_chain(connections):
    p2p = V.P2P_OBJ
    if await p2p.core.create_connection('tipnem.tk', 2000):
        logging.info("1Connect!")
    elif await p2p.core.create_connection('nekopeg.tk', 2000):
        logging.info("2Connect!")

    for host, port in connections:
        await p2p.core.create_connection(host, port)

    # BroadcastProcess setup
    p2p.broadcast_check = broadcast_check

    # Update to newest blockchain
    if await chain_builder.init(V.GENESIS_BLOCK, batch_size=500):
        # only genesisBlock yoy have, try to import bootstrap.dat.gz
        await load_bootstrap_file()
    await sync_chain_loop()

    # Mining/Staking setup
    # Debug.F_CONSTANT_DIFF = True
    # Debug.F_SHOW_DIFFICULTY = True
    # Debug.F_STICKY_TX_REJECTION = False  # for debug
    asyncio.ensure_future(mined_newblock(output_que))
    logging.info("finished all initialization")


def main():
    p = console_args_parser()
    check_process_status(f_daemon=p.daemon)
    set_logger(level=logging.getLevelName(p.log_level), path=p.log_path, f_remove=p.remove_log)
    logging.info(f"\n{__logo__}\n====\nsystem (str) = {__version__}\nchain (int) = {__chain_version__}\n"
                 f"block (int) = {__block_version__}\nmessage = {__message__}")
    connections = setup_client(p2p_port=p.p2p, sub_dir=p.sub_dir)
    loop.run_until_complete(setup_chain(connections))
    loop.run_until_complete(setup_rest_server(user=p.user, pwd=p.password, port=p.rest, host=p.host))
    if p.staking:
        Generate(consensus=C.BLOCK_COIN_POS, power_limit=0.3)
    if p.solo_mining:
        Generate(consensus=C.BLOCK_YES_POW, power_limit=0.05)
        Generate(consensus=C.BLOCK_X16S_POW, power_limit=0.05)
        Generate(consensus=C.BLOCK_X11_POW, power_limit=0.05)
        Generate(consensus=C.BLOCK_CAP_POS, power_limit=0.3, path="E:\\plots")
    blocking_run()


if __name__ == '__main__':
    main()
