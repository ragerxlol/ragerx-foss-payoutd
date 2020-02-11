import json, sys

CREDIT_STATUS_ORPHANED = -1
CREDIT_STATUS_PENDING = 0
CREDIT_STATUS_MATURED = 1

PAYMENT_STATUS_ORPHANED = -1
PAYMENT_STATUS_PENDING = 0
PAYMENT_STATUS_MATURED = 1

BLOCK_STATUS_ORPHANED = -1
BLOCK_STATUS_FAILED = 0
BLOCK_STATUS_OK = 1
BLOCK_STATUS_TX_SEEN = 2
BLOCK_STATUS_CREDITED = 3
BLOCK_STATUS_MATURED = 4
BLOCK_STATUS_CLOSED = 5

with open('config.json') as json_file:
    CONFIG = json.load(json_file)

    PID_FILE = CONFIG['general']['pidfile']

    PAYOUTD_TIMEOUT = CONFIG['general']['interval']
    PAYOUTD_SELF_TEST_TIMEOUT = CONFIG['general']['self_test_timeout']

    BLOCK_MATURE_DEPTH = CONFIG['general']['block_mature_depth']
    BLOCK_ORPHAN_DEPTH = CONFIG['general']['block_orphan_depth']

    PSQL_HOST = CONFIG['postgres']['db_hostname']
    PSQL_PORT = CONFIG['postgres']['db_port']
    PSQL_NAME = CONFIG['postgres']['db_name']
    PSQL_USERNAME = CONFIG['postgres']['db_username']
    PSQL_PASSWORD = CONFIG['postgres']['db_password']

    DAEMON_RPC_HOST = CONFIG['daemon']['hostname']
    DAEMON_RPC_PORT = CONFIG['daemon']['port']

    WALLET_RPC_HOST = CONFIG['wallet']['hostname']
    WALLET_RPC_PORT = CONFIG['wallet']['port']
    WALLET_RPC_AUTH_METHOD = CONFIG['wallet']['rpc_auth_method']
    WALLET_RPC_AUTH_FILE = CONFIG['wallet']['rpc_auth_file']
    WALLET_RPC_USERNAME = CONFIG['wallet']['rpc_username']
    WALLET_RPC_PASSWORD = CONFIG['wallet']['rpc_password']

    COIN_ADDRESS_PREFIXES = CONFIG['coin']['address_prefixes']

    PAYMENTS_PRIORITY = CONFIG['payments']['priority']
    PAYMENTS_MAX_RECIPIENTS = CONFIG['payments']['max_recipients']
    PAYMENTS_RING_SIZE = CONFIG['payments']['ring_size']
    PAYMENTS_WARNING_THRESHOLD = CONFIG['payments']['warning_threshold']
    PAYMENTS_FEE_ADJ_FACTOR = CONFIG['payments']['fee_adjustment_factor']
    PAYMENTS_MAX_PAYMENT_AMOUNT = CONFIG['payments']['max_payment_amount']
    PAYMENTS_NETWORK_BLOCK_INTERVAL = CONFIG['payments']['network_block_interval']

    FEE = CONFIG['fee']['percent']
    FEE_SPLIT = CONFIG['fee']['split']

    LOGGING_PATH = CONFIG['logging']['path']
    LOGGING_PAYOUTD_CONSOLE = CONFIG['logging']['payoutd'] is True or CONFIG['logging']['payoutd'] == 'console' or CONFIG['logging']['payoutd'] == 'both'
    LOGGING_PAYOUTD_FILE    = CONFIG['logging']['payoutd'] is True or CONFIG['logging']['payoutd'] == 'file'    or CONFIG['logging']['payoutd'] == 'both'
    LOGGING_WALLET_CONSOLE  = CONFIG['logging']['wallet'] is True  or CONFIG['logging']['wallet'] == 'console'  or CONFIG['logging']['wallet'] == 'both'
    LOGGING_WALLET_FILE     = CONFIG['logging']['wallet'] is True  or CONFIG['logging']['wallet'] == 'file'     or CONFIG['logging']['wallet'] == 'both'
    LOGGING_DAEMON_CONSOLE  = CONFIG['logging']['daemon'] is True  or CONFIG['logging']['daemon'] == 'console'  or CONFIG['logging']['daemon'] == 'both'
    LOGGING_DAEMON_FILE     = CONFIG['logging']['daemon'] is True  or CONFIG['logging']['daemon'] == 'file'     or CONFIG['logging']['daemon'] == 'both'


# Validate settings

has_error = False

total_split = sum([split['percent'] for split in FEE_SPLIT])
if not total_split == 100:
    print('CONFIG ERROR: Fee split does not add up to 100')
    has_error = True

if int(PAYOUTD_TIMEOUT) != PAYOUTD_TIMEOUT:
    print('CONFIG ERROR: Value interval must be an integer')
    has_error = True

if int(PAYOUTD_SELF_TEST_TIMEOUT) != PAYOUTD_SELF_TEST_TIMEOUT:
    print('CONFIG ERROR: Value self_test_timeout must be an integer')
    has_error = True


if has_error:
    sys.exit()
