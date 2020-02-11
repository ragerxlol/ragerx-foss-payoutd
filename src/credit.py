from math import floor
from time import time

from .constants import *
from . import database, blocks, rpc, log

def record_credit(blk_id, uid, now, reward, bonus_credit, dev_credit):
    """Record calculated credit for a user"""
    try:
        database.execute('INSERT INTO credits (blk_id, uid, time, amount_reward, amount_bonus, amount_dev, status) VALUES (%s, %s, %s, %s, %s, %s, %s)',
                         (blk_id, uid, now, reward, bonus_credit, dev_credit, CREDIT_STATUS_PENDING))
        log.message('Credit user %d on blk %d (reward, bonus, dev): %d %d %d' % (uid, blk_id, reward or 0, bonus_credit or 0, dev_credit or 0))
    except database.psycopg2.Error as e:
        raise Exception(e.pgerror) from None
    except Exception as e:
        log.error('Failed to credit user %d on blk %d (reward, bonus, dev): %d %d %d' % (uid, blk_id, reward or 0, bonus_credit or 0, dev_credit or 0))
        log.error(e)

def update_credit_status(blk_id, status):
    """Change a credit status"""
    try:
        database.execute("UPDATE credits SET status=%s WHERE blk_id = %s", (status, blk_id))
        log.message('Changed credit status on block_id %d status to %s' % (blk_id, status))
    except database.psycopg2.Error as e:
        raise Exception(e.pgerror) from None
    except Exception as e:
        log.error('Failed to change credit status on block_id %d status to %s' % (blk_id, status))
        log.error(e)

def get_pplns_window(timestamp, difficulty):

    pplns_query = """
    SELECT time, running_total
        FROM (
                SELECT time, SUM(count) OVER (ORDER BY time DESC) AS running_total
                FROM valid_shares
                WHERE time <= %s
              ) t
    WHERE running_total <= %s
    ORDER BY time ASC
    LIMIT 1
    """

    database.execute(pplns_query, (timestamp, difficulty))
    return database.fetchone()

def get_user_shares(start_time, end_time):

    share_query = """
    SELECT uid, sum(count)
    FROM valid_shares
    WHERE time BETWEEN %s AND %s
    GROUP BY uid
    """

    database.execute(share_query, (start_time, end_time))
    return database.fetchall()

def calculate():

    now = database.walltime_to_db_time(time())

    # Get uncredited blocks
    unpaid_blocks = blocks.get_blocks_by_status(BLOCK_STATUS_TX_SEEN)

    for block in unpaid_blocks:

        if block['reward'] is None:
            log.message('Block %d at height %d does not have reward set, skipping' % (block['blk_id'], block['height']))
            continue

        blk_id = block['blk_id']
        height = block['height']
        reward = int(block['reward'] * ((100 - FEE) / 100))
        end_time = block['time']
        difficulty = block['difficulty']

        total_credited = 0

        log.message('Calculating credits for block %d' % (height))

        pplns_window = get_pplns_window(end_time, 2 * difficulty)

        if pplns_window is None:
            # This should only happen on testing, means one share > block diff
            log.error('Block %d has too short PPLNS window, skipping...' % (height))
            continue

        start_time = pplns_window[0]
        n_seconds = end_time - start_time

        log.message('Block %d has PPLNS window of %d seconds (diff %d)' % (height, n_seconds, difficulty))

        user_shares = get_user_shares(start_time, end_time)

        total_shares = sum([user_share[1] for user_share in user_shares])

        log.message('Block %d will credit %d miners (total shares %d)' % (height, len(user_shares), total_shares))

        credits_per_uid = {}

        # credit users
        for user_share in user_shares:
            uid, user_shares = user_share
            user_pct = min(1, user_shares / total_shares)
            user_reward = int(user_pct * reward)

            total_credited += user_reward

            if uid not in credits_per_uid:
                credits_per_uid[uid] = {}

            # Credit reward
            log.message('User %d submitted %d shares for %f%% of the block' % (uid, user_shares, user_pct))
            credits_per_uid[uid]['reward'] = user_reward


        # Credit devs
        total_dev_fee = block['reward'] - total_credited
        log.message('Total credits for block %s is %s leaving %d for devfee' % (height, total_credited, total_dev_fee))

        for dev in FEE_SPLIT:
            dev_uid = dev['uid']
            dev_fee_amount = floor(total_dev_fee * dev['percent'] / 100)
            log.message('Credit %s dev fee to %s' % (dev_fee_amount, dev['name']))

            if dev_uid not in credits_per_uid:
                credits_per_uid[dev_uid] = {}

            credits_per_uid[dev_uid]['dev'] = dev_fee_amount


        # Add credits to db
        for uid in credits_per_uid:
            reward = credits_per_uid[uid].get('reward')
            bonus_credit = credits_per_uid[uid].get('bonus')
            dev_credit = credits_per_uid[uid].get('dev')

            record_credit(blk_id, uid, now, reward, bonus_credit, dev_credit)


        # mark as credited
        blocks.update_block_status(blk_id, height, BLOCK_STATUS_CREDITED)


def unlock():

    matured_blocks = blocks.get_blocks_by_status(BLOCK_STATUS_MATURED)
    for block in matured_blocks:
        blk_id = block['blk_id']
        height = block['height']
        # update credit status
        update_credit_status(blk_id, CREDIT_STATUS_MATURED)
        # mark as closed
        blocks.update_block_status(blk_id, height, BLOCK_STATUS_CLOSED)

    orphaned_blocks = blocks.get_blocks_by_status(BLOCK_STATUS_ORPHANED)
    for block in orphaned_blocks:
        blk_id = block['blk_id']
        # update credit status
        update_credit_status(blk_id, CREDIT_STATUS_ORPHANED)
