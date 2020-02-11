from . import rpc

def get_block(height):
    """Get the block from daemon"""
    return rpc.daemon_rpc('get_block', {'height': height})

def get_fee_estimate():
    """Get the fee estimate from daemon"""
    return rpc.daemon_rpc('get_fee_estimate')

def get_transactions(txids):
    """Get tx details from daemon"""
    parameters = {
        'txs_hashes': txids,
        'decode_as_json': True
    }
    result = rpc.daemon_rpc_other('get_transactions', parameters)
    return result.get('txs', [])
