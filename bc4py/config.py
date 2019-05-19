from rx.subjects import Subject
import atexit


# internal stream by ReactiveX
# doc: https://github.com/ReactiveX/RxPY/blob/develop/notebooks/Getting%20Started.ipynb
stream = Subject()
atexit.register(stream.dispose)


class C:  # Constant
    # base currency info
    BASE_CURRENCY = {
        'name': 'PyCoin',
        'unit': 'PC',
        'digit': 8,
        'address': 'NDUMMYADDRESSAAAAAAAAAAAACRSTTMF',
        'description': 'Base currency',
        'image': None
    }

    # consensus
    BLOCK_GENESIS = 0
    BLOCK_COIN_POS = 1
    BLOCK_CAP_POS = 2  # proof of capacity
    BLOCK_FLK_POS = 3  # proof of fund-lock

    BLOCK_YES_POW = 5
    BLOCK_X11_POW = 6
    BLOCK_HMQ_POW = 7
    BLOCK_LTC_POW = 8
    BLOCK_X16S_POW = 9
    consensus2name = {
        BLOCK_GENESIS: 'GENESIS',
        BLOCK_COIN_POS: 'POS_COIN',
        BLOCK_CAP_POS: 'POS_CAP',
        BLOCK_FLK_POS: 'POS_FLK',
        BLOCK_YES_POW: 'POW_YES',
        BLOCK_X11_POW: 'POW_X11',
        BLOCK_HMQ_POW: 'POW_HMQ',
        BLOCK_LTC_POW: 'POW_LTC',
        BLOCK_X16S_POW: 'POW_X16S',
    }

    # tx type
    TX_GENESIS = 0  # Height0の初期設定TX
    TX_POW_REWARD = 1  # POWの報酬TX
    TX_POS_REWARD = 2  # POSの報酬TX
    TX_TRANSFER = 3  # 送受金
    TX_MINT_COIN = 4  # 新規貨幣を鋳造
    TX_VALIDATOR_EDIT = 8  # change validator info
    TX_CONCLUDE_CONTRACT = 9  # conclude static contract tx
    TX_INNER = 255  # 内部のみで扱うTX
    txtype2name = {
        TX_GENESIS: 'GENESIS',
        TX_POW_REWARD: 'POW_REWARD',
        TX_POS_REWARD: 'POS_REWARD',
        TX_TRANSFER: 'TRANSFER',
        TX_MINT_COIN: 'MINT_COIN',
        TX_VALIDATOR_EDIT: 'VALIDATOR_EDIT',
        TX_CONCLUDE_CONTRACT: 'CONCLUDE_CONTRACT',
        TX_INNER: 'TX_INNER'
    }

    # message format
    MSG_NONE = 0  # no message
    MSG_PLAIN = 1  # 明示的にunicode
    MSG_BYTE = 2  # 明示的にbinary
    MSG_MSGPACK = 3  # msgpack protocol
    MSG_HASHLOCKED = 4  # hash-locked transaction
    msg_type2name = {
        MSG_NONE: 'NONE',
        MSG_PLAIN: 'PLAIN',
        MSG_BYTE: 'BYTE',
        MSG_MSGPACK: 'MSGPACK',
        MSG_HASHLOCKED: 'HASHLOCKED'
    }

    # difficulty
    DIFF_RETARGET = 20  # difficultyの計算Block数

    # address params
    ADDR_NORMAL_VER = 0
    ADDR_VALIDATOR_VER = 1
    ADDR_CONTRACT_VER = 2
    BIP44_COIN_TYPE = 0x800002aa

    # block params
    MATURE_HEIGHT = 20  # 採掘されたBlockのOutputsが成熟する期間

    # account
    ANT_UNKNOWN = 0  # Unknown user
    ANT_VALIDATOR = 1  # ValidatorAddress
    ANT_CONTRACT = 2  # ContractAddress
    ANT_STAKED = 3  # Staked balance
    account2name = {
        ANT_UNKNOWN: '@Unknown',
        ANT_VALIDATOR: '@Validator',
        ANT_CONTRACT: '@Contract',
        ANT_STAKED: '@Staked',
    }

    # Block/TX/Fee limit
    SIZE_BLOCK_LIMIT = 300 * 1000  # 300kb block
    SIZE_TX_LIMIT = 100 * 1000  # 100kb tx
    CASHE_LIMIT = 300  # Memoryに置く最大Block数、実質Reorg制限
    BATCH_SIZE = 30
    MINTCOIN_GAS = int(10 * pow(10, 6))  # 新規Mintcoin発行GasFee
    SIGNATURE_GAS = int(0.01 * pow(10, 6))  # gas per one signature
    # CONTRACT_CREATE_FEE = int(10 * pow(10, 6))  # コントラクト作成GasFee
    VALIDATOR_EDIT_GAS = int(10 * pow(10, 6))  # gas
    CONTRACT_MINIMUM_INPUT = int(1 * pow(10, 8))  # Contractの発火最小amount

    # network params
    ACCEPT_MARGIN_TIME = 120  # 新規データ受け入れ時間マージンSec
    MAX_RECURSIVE_BLOCK_DEPTH = 30  # recursive accept block limit

    # sqlite params
    SQLITE_CASHE_SIZE = None  # if None, size is 2000
    SQLITE_JOURNAL_MODE = 'WAL'  # if None, mode is DELETE
    SQLITE_SYNC_MODE = 'NORMAL'  # if None, sync is FULL


class V:
    # Blockchain basic params
    GENESIS_BLOCK = None
    GENESIS_PARAMS = None
    BLOCK_GENESIS_TIME = None
    BLOCK_TIME_SPAN = None
    BLOCK_MINING_SUPPLY = None
    BLOCK_REWARD = None
    BLOCK_BASE_CONSENSUS = None
    BLOCK_CONSENSUSES = None

    # base coin
    COIN_DIGIT = None
    COIN_MINIMUM_PRICE = None  # Gasの最小Price

    # database path
    DB_HOME_DIR = None
    DB_ACCOUNT_PATH = None

    # Wallet
    BECH32_HRP = None  # human readable part
    EXTENDED_KEY_OBJ = None  # <Bip32 m/44'/coinType'> object

    # mining
    MINING_ADDRESS = None
    PC_OBJ = None  # P2P peer client object
    API_OBJ = None  # REST API object

    # developer
    BRANCH_NAME = None  # Github branch name


class P:  # 起動中もダイナミックに変化
    F_STOP = False  # Stop signal
    F_NOW_BOOTING = True  # Booting mode flag


class Debug:
    F_SHOW_DIFFICULTY = False
    F_CONSTANT_DIFF = False
    F_STICKY_TX_REJECTION = True


class BlockChainError(Exception):
    pass


__all__ = [
    'stream',
    'C',
    'V',
    'P',
    'Debug',
    'BlockChainError',
]

