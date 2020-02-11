from .constants import *
from .errors import *
from . import database, wallet, rpc, log

def update_block_reward(blk_id, height, reward, reward_total):
    """Change a block info"""
    try:
        database.execute("UPDATE mined_blocks SET reward=%s, reward_total=%s WHERE blk_id = %s", (reward, reward_total, blk_id))
        log.message('Updated block %d at height %d for reward (total): %d (%d)' % (blk_id, height, reward, reward_total))
    except database.psycopg2.Error as e:
        raise Exception(e.pgerror) from None
    except Exception as e:
        log.error('Failed to update block %d at height %d for reward (total): %d (%d)' % (blk_id, height, reward, reward_total))
        log.error(e)

def update_block_status(blk_id, height, status):
    """Change a block status"""
    try:
        database.execute("UPDATE mined_blocks SET status=%s WHERE blk_id = %s", (status, blk_id))
        log.message('Updated block %d at height %d status to %s' % (blk_id, height, status))
    except database.psycopg2.Error as e:
        raise Exception(e.pgerror) from None
    except Exception as e:
        log.message('Failed to update block %d at height %d status to %s' % (blk_id, height, status))
        log.error(e)

def get_blocks_by_status(status):
    try:
        database.execute("SELECT blk_id, txid, height, difficulty, time, uid, reward, status FROM mined_blocks WHERE status=%s", (status,))
        result = database.fetchall()
        for idx in range(len(result)):
            result[idx] = {
                'blk_id': result[idx][0],
                'txid': result[idx][1],
                'height': result[idx][2],
                'difficulty': result[idx][3],
                'time': result[idx][4],
                'uid': result[idx][5],
                'reward': result[idx][6],
                'status': result[idx][7]
            }
        return result
    except database.psycopg2.Error as e:
        raise Exception(e.pgerror) from None
    except Exception as e:
        log.error(e)
        raise RecoverableError('Failed to get blocks by status') from None

def get_non_mature_blocks():
    try:
        database.execute('SELECT blk_id, height, txid, status FROM mined_blocks WHERE status BETWEEN %s AND %s', (BLOCK_STATUS_OK, BLOCK_STATUS_CREDITED))
        blocks = database.fetchall()
        return blocks
    except database.psycopg2.Error as e:
        raise Exception(e.pgerror) from None
    except Exception as e:
        log.error(e)
        raise RecoverableError('Failed to get non mature blocks') from None

def unlock_blocks():
    """Update blocks statuses"""

    wallet_height = wallet.get_wallet_height()

    # Get non-matured blocks
    blocks = get_non_mature_blocks()

    # For each status-0 or status-1 block
    for block in blocks:

        blk_id, height, txid, status = block

        # Get the transaction from wallet-rpc
        # this shows us how much the pool received as a reward
        try:
            transfers = rpc.wallet_rpc('get_transfers', {'in': True, 'filter_by_height': True, 'min_height': height - 1, 'max_height': height})
        except:
            log.error('Failed to get transfers for block at height %d, skipping' % (height,))
            continue

        tx_seen = False
        amount = 0

        if 'in' in transfers:
            for t in transfers['in']:
                if t['height'] == height and t['type'] == 'block' and t['txid'] == txid:
                    tx_seen = True
                    amount = t['amount']
                    break

        # Get the transaction from daemon-rpc
        # this shows us how much the total block reward was
        try:
            block_daemon = rpc.daemon_rpc('get_block', {'height': height})
        except:
            log.error('Failed to get info for block at height %d, skipping' % (height,))
            continue

        amount_total = block_daemon['block_header']['reward']

        # If transaction is seen
        if tx_seen:

            # If block has been credited and we are outside at-risk zone, set to MATURED
            if status == BLOCK_STATUS_CREDITED and wallet_height > height + BLOCK_MATURE_DEPTH:
                update_block_status(blk_id, height, BLOCK_STATUS_MATURED)

            # If block is not yet marked as tx seen, set to TX_SEEN
            elif status < BLOCK_STATUS_TX_SEEN:
                update_block_reward(blk_id, height, amount, amount_total)
                update_block_status(blk_id, height, BLOCK_STATUS_TX_SEEN)

        # If transaction is not seen, and we are at least 10 blocks away, orphan
        elif wallet_height > height + BLOCK_ORPHAN_DEPTH:
            update_block_status(blk_id, height, BLOCK_STATUS_ORPHANED)
