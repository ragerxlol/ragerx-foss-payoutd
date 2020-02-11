from time import time
import json
import hashlib
import re

from cryptonote.address import validate

from .constants import *
from .errors import *
from . import database, credit, blocks, fee, wallet, daemon, rpc, log

def record_payment(uid, txid, time, amount, fee):
    """Record payment"""
    try:
        database.execute('INSERT INTO payments (uid, txid, time, amount_paid, amount_fee, status) VALUES (%s, %s, %s, %s, %s, %s)',
                         (uid, txid, time, amount, fee, PAYMENT_STATUS_PENDING))
        log.message('Recorded payment for user %s, txid: %s, time: %s, amount: %s, fee: %s' % (uid, txid, time, amount, fee))
        return True
    except database.psycopg2.Error as e:
        raise Exception(e.pgerror) from None
    except Exception as e:
        log.error('Failed to record payment for user %s, txid: %s, time: %s, amount: %s, fee: %s' % (uid, txid, time, amount, fee))
        log.error(e)
        return False

def update_payment_status(pymt_id, txid, txhash, status):
    """Change payment status"""
    try:
        database.execute("UPDATE payments SET txid=%s, txhash=%s, status=%s WHERE pymt_id=%s", (txid, txhash, status, pymt_id))
        log.message('Updated payment status for pymt %s, txid: %s, txhash: %s, status: %s' % (pymt_id, txid, txhash, status))
        return True
    except database.psycopg2.Error as e:
        raise Exception(e.pgerror) from None
    except Exception as e:
        log.error('Failed to update payment status for pymt %s, txid: %s, txhash: %s, status: %s' % (pymt_id, txid, txhash, status))
        log.error(e)
        return False

def update_failed_payment_status(pymt_id, txid, txhash, amount_fee):
    """Change payment status for payments with null txid"""
    try:
        database.execute("UPDATE payments SET txid=%s, txhash=%s, amount_fee=%s WHERE pymt_id=%s", (txid, txhash, amount_fee, pymt_id))
        log.message('Updated null payment %s, txid: %s, txhash: %s, fee: %s' % (pymt_id, txid, txhash, amount_fee))
        return True
    except database.psycopg2.Error as e:
        raise Exception(e.pgerror) from None
    except Exception as e:
        log.error('Failed to update null payment %s, txid: %s, txhash: %s, fee: %s' % (pymt_id, txid, txhash, amount_fee))
        log.error(e)
        return False

def get_pending_payments():
    """Get rows from payments table where status = 0"""
    try:
        database.execute("SELECT pymt_id, txhash, txid, amount_paid FROM payments WHERE status = %s", (PAYMENT_STATUS_PENDING,))
        return database.fetchall()
    except database.psycopg2.Error as e:
        raise Exception(e.pgerror) from None
    except Exception as e:
        log.error('Failed to get pending payments')
        log.error(e)
        return []

def get_balances_and_thresholds():
    """Get users sum of credits, sum of payment, user threshold and wallet address"""
    try:
        query = """
        SELECT
        info.uid,
        info.wallet,
        info.payment_threshold,
        COALESCE(credits_pending.sum, 0),
        COALESCE(credits_matured.sum, 0),
        COALESCE(debits.sum, 0)
        FROM (
          SELECT
          uid,
          payment_threshold,
          wallet
          FROM users
        ) AS info
        LEFT JOIN (
          SELECT
          uid,
          SUM(
            COALESCE(amount_reward, 0) +
            COALESCE(amount_bonus, 0) +
            COALESCE(amount_dev, 0)
          ) AS sum
          FROM credits
          WHERE status = 0
          GROUP BY uid
        ) AS credits_pending ON credits_pending.uid = info.uid
        LEFT JOIN (
          SELECT
          uid,
          SUM(
            COALESCE(amount_reward, 0) +
            COALESCE(amount_bonus, 0) +
            COALESCE(amount_dev, 0)
          ) AS sum
          FROM credits
          WHERE status = 1
          GROUP BY uid
        ) AS credits_matured ON credits_matured.uid = info.uid
        LEFT JOIN (
          SELECT
          uid,
          SUM(
            COALESCE(payments.amount_paid, 0) +
            COALESCE(payments.amount_fee, 0)
          ) AS sum
          FROM payments
          WHERE status <> -1
          GROUP BY uid
        ) AS debits ON debits.uid = info.uid
        """

        database.execute(query)

        return database.fetchall()

    except database.psycopg2.Error as e:
        raise Exception(e.pgerror) from None
    except Exception as e:
        log.error('Failed to get balances and thresholds')
        log.error(e)
        return []

def make_payments():
    """Pay payments based on credits"""

    # i.e. [ { uid, addr_type, amount, address }, ... ]
    payments = []

    now = database.walltime_to_db_time(time())

    users = get_balances_and_thresholds()

    total_matured = 0
    total_pending = 0

    log.message('Building list of payments')

    for user in users:
        uid, wallet_addr, payment_threshold, credits_pending, credits_matured, debits = user

        confirmed_balance = credits_matured - debits

        total_matured += confirmed_balance
        total_pending += credits_pending

        if confirmed_balance < payment_threshold:
            continue

        # Limit the amount to pay to PAYMENTS_MAX_PAYMENT_AMOUNT because if
        # it is a really large amount, will get "tx not possible"
        amount_to_pay = min(confirmed_balance, PAYMENTS_MAX_PAYMENT_AMOUNT)

        wallet_info = validate(wallet_addr, COIN_ADDRESS_PREFIXES)

        if not wallet_info['valid']:
            log.error('User with uid %d has an invalid address %s, skipping...' % (uid, wallet_addr))
            continue

        # Append to payments array
        payments.append({ 'uid': uid, 'addr_type': wallet_info['type'], 'amount': amount_to_pay, 'address': wallet_addr })

    # sort payments by lowest amount first
    payments = sorted(payments, key=lambda k: k['amount'])

    log.message('Building list of payments... DONE')
    if not len(payments):
        log.message('No payments need to be made now')

    balance, unlocked_balance = wallet.get_balance()
    net_difference = balance - int(total_matured+total_pending)
    log.message('')
    log.message('Accounting check')
    log.message('Wallet:')
    log.message('==========================================================')
    log.message('|     balance      |     unlocked     |      locked      |')
    log.message('==========================================================')
    log.message('|%s|%s|%s|' % (str(balance).rjust(18), str(unlocked_balance).rjust(18), str(int(balance-unlocked_balance)).rjust(18)))
    log.message('==========================================================')
    log.message('')
    log.message('Owed to users:')
    log.message('==========================================================')
    log.message('|      total       |    confirmed     |   unconfirmed    |')
    log.message('==========================================================')
    log.message('|%s|%s|%s|' % (str(int(total_matured+total_pending)).rjust(18), str(total_matured).rjust(18), str(total_pending).rjust(18)))
    log.message('==========================================================')
    log.message('')
    log.message('Net (balance - owed): %d' % (net_difference,))
    log.message('')

    if net_difference < -1 * PAYMENTS_WARNING_THRESHOLD:
        log.error('We owe more than we have in the wallet, quitting...')
        raise CriticalPaymentError()

    out_of_money = False

    # Continue building transactions until we run out of money or payees
    while not out_of_money and len(payments):

        balance, unlocked_balance = wallet.get_balance()

        log.message('Building transaction')
        log.message('Wallet has unlocked balance of: %d' % (unlocked_balance))

        # payments that will be made in this transaction
        recipients = []

        running_total = 0

        if payments[0]['addr_type'] == 'integrated':
            log.message('This will be an exchange payment')
            if payments[0]['amount'] <= unlocked_balance:
                log.message('We have enough money')
                running_total = payments[0]['amount']
                recipients = payments.pop(0)
            else:
                log.message('We do not have enough money')
                out_of_money = True
                break
        else:
            log.message('This will be a normal payment')
            i = 0
            while len(recipients) < PAYMENTS_MAX_RECIPIENTS and i < len(payments):
                if payments[i]['addr_type'] == 'integrated':
                    i += 1
                    continue
                if running_total + payments[i]['amount'] <= unlocked_balance:
                    running_total += payments[i]['amount']
                    recipients.append(payments.pop(i))
                else:
                    out_of_money = True
                    break

            if not out_of_money:
                log.message('We have enough money')
            elif len(recipients):
                log.message('We have enough money for partial payment')
            else:
                log.message('We do not have enough money')
                break

        log.message('Attempting transaction to pay %d users a total of %d' % (len(recipients), running_total))

        fee_estimated = PAYMENTS_FEE_ADJ_FACTOR * fee.estimate_fee(recipients)
        fee_per_user = fee.split_fee(fee_estimated, len(recipients))

        # this will hold recipient info with only amount and address for RPC
        recipients_rpc = []

        for recipient in recipients:
            # subtract estimated fee for each user
            recipient['amount'] = int(recipient['amount'] - fee_per_user)

            # push this address into the wallet rpc list
            recipients_rpc.append({ 'amount': recipient['amount'], 'address': recipient['address'] })

        # Make the actual transfer
        try:
            result = wallet.transfer(recipients_rpc)

            txid = result['tx_hash']
            fee_actual = result['fee']
            fee_actual_per_user = fee.split_fee(fee_actual, len(recipients))

            log.message('Transaction success with txid %s' % (txid,))
            log.message('Estimated fee - actual fee: %s - %s = %s' % (fee_estimated, fee_actual, fee_estimated - fee_actual))

        except rpc.RpcError as re:
            log.error('Error transferring payment, reason: %s' % (re,))
            log.error(recipients)

            # If RPC failed, we will still record debit with estimated fee and empty txid
            txid = None
            fee_actual_per_user = fee_per_user

        for recipient in recipients:
            uid = recipient['uid']
            amount = recipient['amount']

            # record payment and fee
            log.message('Debit user %s (amount, fee): %s %s' % (uid, amount, fee_actual_per_user))
            if not record_payment(uid, txid, now, amount, fee_actual_per_user):
                log.error('Critical: failed to record payment for user %d' % (uid,))
                raise CriticalPaymentError()

def unlock():

    # get all payments in at-risk zone from db
    payments_db = get_pending_payments()

    if len(payments_db) == 0:
        # nothing to do
        return

    # calculate at-risk zone
    start_height, wallet_height = wallet.get_at_risk_zone()

    log.message('Wallet height is %s, at risk zone is %s' % (wallet_height, start_height))

    # get all payments in at-risk zone from rpc
    payments_rpc = wallet.get_outgoing_transfers(start_height)

    # dict to hold txids and their destinations
    # If we don't have a txid in db, use this to match by amount
    txids = {}
    for payment in payments_rpc:
        txids[payment['txid']] = {
            'destinations': payment['destinations'],
            'fee_per_user': fee.split_fee(payment['fee'], len(payment['destinations']))
        }

    # get the tx info from daemon
    transactions = daemon.get_transactions(list(txids.keys()))

    # dict to hold tx hashes and their txid
    tx_hashes = {}

    # calculate txhash from all payments in rpc
    for transaction in transactions:
        txid = transaction['tx_hash']
        block_height = transaction.get('block_height', 0)
        tx_as_json = json.loads(transaction['as_json'])

        # concats all the output key images in this tx
        k_image_concat = ''.join([vout['target']['key'] for vout in tx_as_json['vout']])

        # hash key images with sha256
        tx_hash = hashlib.sha256(bytes.fromhex(k_image_concat)).hexdigest()

        tx_hashes[tx_hash] = [txid, block_height]

    needs_rescan = False

    # loop though pending payments from db
    for payment in payments_db:
        pymt_id, tx_hash, txid, amount_paid = payment

        if txid is None:
            # we had an error submitting payment, skip for now
            # we will try and match this up by amount later
            continue

        if tx_hash is None:
            # we just submitted this payment, find the tx hash
            for key, val in tx_hashes.items():
                if val[0] == txid:
                    tx_hash = key
                    break

            if tx_hash is None:
                # if new tx is not found in daemon, we need to skip for now
                log.error('Payment id %d with txid %s not found in daemon immediately after payment' % (pymt_id, txid))
                continue
            else:
                update_payment_status(pymt_id, txid, tx_hash, PAYMENT_STATUS_PENDING)


        if tx_hash in tx_hashes:
            # we are still seeing this tx
            txid_new, block_height = tx_hashes[tx_hash]

            # delete txid_new from txids dict to mark it as accounted for
            if txid_new in txids:
                txids.pop(txid_new)

            # transaction malleability check
            if txid != txid_new:
                log.message('Transaction malleability check warning, txid %s -> %s' % (txid, txid_new))
                update_payment_status(pymt_id, txid_new, tx_hash, PAYMENT_STATUS_PENDING)

            # check if tx is matured
            if block_height != 0 and wallet_height > block_height + BLOCK_MATURE_DEPTH:
                log.message('Transaction matured, txid %s' % (txid,))
                update_payment_status(pymt_id, txid, tx_hash, PAYMENT_STATUS_MATURED)

        else:
            # this tx is orphaned
            log.message('Transaction orphaned, txid %s' % (txid,))
            update_payment_status(pymt_id, txid, tx_hash, PAYMENT_STATUS_ORPHANED)
            needs_rescan = True

    # Loop through payments_db again looking for payments that have an null txid
    # at this point, we have removed any accounted for payments from txids dict
    for payment in payments_db:
        pymt_id, tx_hash, txid, amount_paid = payment
        fee_per_user = None

        if not txid is None:
            # we only care about payments without a txid
            continue

        log.message('Payment %s has null txid, attempting to fix' % (pymt_id,))

        # Search through txid dict to match this payment by amount_paid
        for txid_search in txids:
            for recipient in txids[txid_search]['destinations']:
                if amount_paid == recipient['amount']:
                    txid = txid_search
                    fee_per_user = txids[txid_search]['fee_per_user']
                    break

        if txid is None:
            # we still have no txid, skip
            log.error('Cannot find txid for null payment %s, might have failed completely' % (pymt_id,))
            continue

        log.message('Found txid for null payment %s, %s' % (pymt_id,txid))

        # Find the tx_hash
        for key, val in tx_hashes.items():
            if val[0] == txid:
                tx_hash = key
                break

        if tx_hash is None:
            # if new tx is not found in daemon, we need to skip for now
            log.error('Payment id %d with txid %s not found in daemon immediately after payment' % (pymt_id, txid))
            continue

        update_failed_payment_status(pymt_id, txid, tx_hash, fee_per_user)


    if needs_rescan:
        log.message('Rescanning wallet')
        if wallet.rescan_bc():
            log.message('Rescan complete')
        else:
            log.error('Rescan error')
