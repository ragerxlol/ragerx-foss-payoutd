import requests
import json
import os

from .constants import *
from .errors import *
from . import log

def check_rpc():
    try:
        daemon_rpc('get_info')
        log.message('Connected to daemon rpc')
        wallet_rpc('get_version')
        log.message('Connected to wallet rpc')
        return True
    except RpcError:
        return False

def wallet_rpc(s_method, d_params=None):
    """Call wallet RPC"""
    try:
        d_headers = {'Content-Type': 'application/json'}
        d_rpc_input = {"jsonrpc": "2.0", "id": "0", "method" :  s_method}

        if d_params is not None:
            d_rpc_input['params'] = d_params

        log.message_wallet_rpc('req', json.dumps(d_rpc_input))

        if WALLET_RPC_AUTH_METHOD == 'file':
            with open(WALLET_RPC_AUTH_FILE, 'r') as f:
                username, password = f.readline().split(':')
        else:
            username, password = [WALLET_RPC_USERNAME, WALLET_RPC_PASSWORD]

        o_rsp = requests.post('http://' + WALLET_RPC_HOST + ':' + str(WALLET_RPC_PORT) + '/json_rpc',
                              data=json.dumps(d_rpc_input),
                              headers=d_headers,
                              timeout=300.0, # Wallet can be fairly slow for large requests
                              auth=requests.auth.HTTPDigestAuth(WALLET_RPC_USERNAME, WALLET_RPC_PASSWORD))

        if o_rsp.status_code != requests.codes.ok: # pylint: disable=maybe-no-member
            raise RpcError(o_rsp.reason)

        d_jsn = o_rsp.json()

        log.message_wallet_rpc('res', d_jsn)

        if 'error' in d_jsn:
            raise RpcError(d_jsn['error']['message'])

        return d_jsn['result']

    except RpcError as e:
        log.error_wallet_rpc(e)
        raise
    except requests.exceptions.RequestException as e:
        log.error_wallet_rpc(e)
        raise RpcError(e)
    except OSError as e:
        log.message(e)
        log.error_wallet_rpc(e)
        raise RpcError(e)
    except:
        log.error_wallet_rpc('Unknown')
        raise RpcError('Unknown')

def daemon_rpc(s_method, d_params=None):
    try:
        d_headers = {'Content-Type': 'application/json'}
        d_daemon_input = {"jsonrpc": "2.0", "id": "0", "method" :  s_method}

        if d_params is not None:
            d_daemon_input['params'] = d_params

        log.message_daemon_rpc('req', d_daemon_input)

        o_rsp = requests.post('http://' + DAEMON_RPC_HOST + ':' + str(DAEMON_RPC_PORT) + '/json_rpc',
                              data=json.dumps(d_daemon_input),
                              headers=d_headers,
                              timeout=300.0)

        if o_rsp.status_code != requests.codes.ok: # pylint: disable=maybe-no-member
            raise RpcError(o_rsp.reason)

        d_jsn = o_rsp.json()

        log.message_daemon_rpc('res', d_jsn)

        if 'error' in d_jsn:
            raise RpcError(d_jsn['error']['message'])

        return d_jsn['result']

    except RpcError as e:
        log.error_daemon_rpc(e)
        raise
    except requests.exceptions.RequestException as e:
        log.error_daemon_rpc(e)
        raise RpcError(e)
    except:
        log.error_daemon_rpc('Unknown')
        raise RpcError('Unknown')

def daemon_rpc_other(s_method, d_params=None):
    try:
        d_headers = {'Content-Type': 'application/json'}

        log.message_daemon_rpc('req', 'method: %s params: %s' % (s_method, d_params))

        o_rsp = requests.post('http://' + DAEMON_RPC_HOST + ':' + str(DAEMON_RPC_PORT) + '/' + s_method,
                              data=json.dumps(d_params),
                              headers=d_headers,
                              timeout=300.0)

        if o_rsp.status_code != requests.codes.ok: # pylint: disable=maybe-no-member
            raise RpcError(o_rsp.reason)

        d_jsn = o_rsp.json()

        log.message_daemon_rpc('res', d_jsn['status'])

        if 'error' in d_jsn:
            raise RpcError(d_jsn['error']['message'])

        return d_jsn

    except RpcError as e:
        log.error_daemon_rpc(e)
        raise
    except requests.exceptions.RequestException as e:
        log.error_daemon_rpc(e)
        raise RpcError(e)
    except:
        log.error_daemon_rpc('Unknown')
        raise RpcError('Unknown')
