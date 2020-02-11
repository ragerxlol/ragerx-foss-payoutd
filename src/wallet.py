from .constants import *
from .errors import *
from . import database, rpc

def get_wallet_height():
    """Get the wallet's current block height"""
    try:
        return rpc.wallet_rpc('get_height')['height']
    except RpcError:
        raise RecoverableError('Failed to call wallet-rpc get_height') from None

def get_balance():
    """Get the wallet's balance"""
    try:
        result = rpc.wallet_rpc('get_balance')
        return result['balance'], result['unlocked_balance']
    except RpcError:
        raise RecoverableError('Failed to call wallet-rpc get_balance') from None

def get_outgoing_transfers(min_height):
    """Get outgoing transfers starting at min_height"""
    try:
        parameters = {
            'out': True,
            'pending': True,
            'filter_by_height': True,
            'min_height': min_height
        }
        result = rpc.wallet_rpc('get_transfers', parameters)

        transfers = []
        if 'pending' in result:
            transfers += result['pending']
        if 'out' in result:
            transfers += result['out']

        return transfers
    except RpcError:
        raise RecoverableError('Failed to call wallet-rpc get_transfers') from None

def transfer(destinations, payment_id=None):
    """Make a wallet rpc transfer"""
    # exceptions are handled in payments.py
    parameters = {
        'destinations': destinations,
        'priority': PAYMENTS_PRIORITY,
        'ring_size': PAYMENTS_RING_SIZE,
        # 'do_not_relay': True
    }

    if payment_id is not None:
        parameters['payment_id'] = payment_id

    return rpc.wallet_rpc('transfer', parameters)

def get_at_risk_zone():
    wallet_height = get_wallet_height()
    last_scan_height = get_last_scan_height()
    return max(0, min(wallet_height - BLOCK_MATURE_DEPTH - 10, last_scan_height - BLOCK_MATURE_DEPTH - 10)), wallet_height

def get_last_scan_height():
    """Get last scan height from db"""
    try:
        database.execute('SELECT height, time FROM scan_height')
        rows = database.fetchall()

        if len(rows) == 0:
            log.error('Table scan_height has no rows')
            return 0

        elif len(rows) == 1:
            return rows[0][0]

        else:
            log.error('Table scan_height has more than one row')
            # get the lowest value
            heights = [row[0] for row in rows]
            return min(heights)

    except database.psycopg2.Error as e:
        raise Exception(e.pgerror) from None
    except Exception as e:
        log.error(e)
        raise RecoverableError('Failed to get last scan height from database') from None

def update_last_scan_height(height, time):
    """Update last scan height in db"""
    try:
        database.execute('UPDATE scan_height SET height = %s, time = %s', (height, time))
        return True
    except database.psycopg2.Error as e:
        raise Exception(e.pgerror) from None
    except Exception as e:
        log.error('Failed to update last scan height')
        log.error(e)
        return False

def rescan_bc():
    """Rescan wallet bc"""
    try:
        rpc.wallet_rpc('rescan_blockchain')
        return True
    except RpcError:
        log.error('Failed to rescan blockchain')
        return False
