from math import floor, ceil

from .constants import *
from . import daemon, log

def split_fee(fee, n):
    return floor(fee / n)

def estimate_fee(recipients):

    extra = 0

    # for recipient in recipients:
    #     # if sub address, add N bytes
    #     if 'payment_id' in recipient:
    #         extra += 32


    bytes_no = estimate_rct_tx_size(n_inputs=4, mixin=PAYMENTS_RING_SIZE - 1, n_outputs=len(recipients) + 1, extra_size=extra, bulletproof=True)

    fee_multiplier = get_fee_multiplier(PAYMENTS_PRIORITY)

    fee_per_b = fee_per_b_default()
    quantization_mask = fee_quantization_mask_default()

    try:
        result = daemon.get_fee_estimate()
        fee_per_b = result['fee']
        quantization_mask = result['quantization_mask']
    except:
        log.error('Failed to get_fee_estimate from daemon')

    fee = int(ceil(fee_per_b * bytes_no / quantization_mask) * quantization_mask)

    return fee

def default_priority():
    return 1

def fee_per_b_default():
    return 2000000000

def fee_quantization_mask_default():
    return 10000

def get_fee_multiplier(priority):
    multipliers = [1, 5, 25, 1000]
    if priority <= 0:
        priority = default_priority()

    priority -= 1

    if priority >= len(multipliers):
        priority = len(multipliers) - 1

    return multipliers[priority]


def estimate_rct_tx_size(n_inputs, mixin, n_outputs, extra_size, bulletproof):
    size = 0

    #  tx prefix

    # first few bytes
    size += 1 + 6

    # vin
    size += n_inputs * (1 + 6 + (mixin + 1) * 2 + 32)

    # vout
    size += n_outputs * (6 + 32)

    # extra
    size += extra_size

    # rct signatures

    # type
    size += 1

    # rangeSigs
    if bulletproof:
        size += ((2 * 6 + 4 + 5) * 32 + 3) * n_outputs

        # log_padded_outputs = 0
        # while (1<<log_padded_outputs) < n_outputs:
        #     ++log_padded_outputs
        # size += (2 * (6 + log_padded_outputs) + 4 + 5) * 32 + 3
    else:
        size += (2 * 64 * 32 + 32 + 64 * 32) * n_outputs

    # MGs
    size += n_inputs * (64 * (mixin + 1) + 32)

    # mixRing - not serialized, can be reconstructed
    # size += 2 * 32 * (mixin+1) * n_inputs

    # pseudoOuts
    size += 32 * n_inputs
    # ecdhInfo
    size += 2 * 32 * n_outputs
    # outPk - only commitment is saved
    size += 32 * n_outputs
    # txnFee
    size += 4

    return size
