import datetime, time, os
from colorama import init as colorama_init, Fore

from .constants import *

colorama_init(autoreset=True)

PAYOUTD_LOG_FILE = False
WALLET_LOG_FILE = False
DAEMON_LOG_FILE = False

def open_log_files():
    global PAYOUTD_LOG_FILE, WALLET_LOG_FILE, DAEMON_LOG_FILE
    if LOGGING_PAYOUTD_FILE:
        PAYOUTD_LOG_FILE = open(os.path.join(LOGGING_PATH, 'payoutd.log'), 'a+')
    if LOGGING_WALLET_FILE:
        WALLET_LOG_FILE = open(os.path.join(LOGGING_PATH, 'wallet.log'), 'a+')
    if LOGGING_DAEMON_FILE:
        DAEMON_LOG_FILE = open(os.path.join(LOGGING_PATH, 'daemon.log'), 'a+')

open_log_files()

def ts():
    return datetime.datetime.fromtimestamp(time.time()).strftime('%Y-%m-%d %H:%M:%S')


def message(msg=''):
    """Print out messages"""
    message = ts() + '[INFO] ' + str(msg)
    if LOGGING_PAYOUTD_CONSOLE:
        print(Fore.BLUE + message + Fore.RESET)
    if LOGGING_PAYOUTD_FILE:
        PAYOUTD_LOG_FILE.write(message + '\n')
        PAYOUTD_LOG_FILE.flush()


def error(msg=''):
    """Print out error"""
    message = ts() + '[ERROR] ' + str(msg)
    if LOGGING_PAYOUTD_CONSOLE:
        print(Fore.RED + message + Fore.RESET)
    if LOGGING_PAYOUTD_FILE:
        PAYOUTD_LOG_FILE.write(message + '\n')
        PAYOUTD_LOG_FILE.flush()


def message_wallet_rpc(REQorRES, msg=''):
    """Print out messages for wallet RPC calls"""
    if REQorRES == 'req':
        message = ts() + '[WALLET][REQ] ' + str(msg)
    elif REQorRES == 'res':
        message = ts() + '[WALLET][RES] ' + str(msg)
    else:
        return

    if LOGGING_WALLET_CONSOLE:
        print(message)
    if LOGGING_WALLET_FILE:
        WALLET_LOG_FILE.write(message + '\n')
        WALLET_LOG_FILE.flush()


def error_wallet_rpc(msg=''):
    """Print out errors for wallet RPC calls"""
    message = ts() + '[WALLET][ERROR] ' + str(msg)
    if LOGGING_WALLET_CONSOLE:
        print(Fore.RED + message + Fore.RESET)
    if LOGGING_WALLET_FILE:
        WALLET_LOG_FILE.write(message + '\n')
        WALLET_LOG_FILE.flush()


def message_daemon_rpc(REQorRES, msg=''):
    """Print out messages for daemon RPC calls"""
    if REQorRES == 'req':
        message = ts() + '[DAEMON][REQ] ' + str(msg)
    elif REQorRES == 'res':
        message = ts() + '[DAEMON][RES] ' + str(msg)
    else:
        return

    if LOGGING_DAEMON_CONSOLE:
        print(message)
    if LOGGING_DAEMON_FILE:
        DAEMON_LOG_FILE.write(message + '\n')
        DAEMON_LOG_FILE.flush()


def error_daemon_rpc(msg=''):
    """Print out errors for daemon RPC calls"""
    message = ts() + '[DAEMON][ERROR] ' + str(msg)
    if LOGGING_DAEMON_CONSOLE:
        print(Fore.RED + message + Fore.RESET)
    if LOGGING_DAEMON_FILE:
        DAEMON_LOG_FILE.write(message + '\n')
        DAEMON_LOG_FILE.flush()
