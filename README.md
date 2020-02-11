# ragerx-foss-payoutd

Open source (BSD-3) payout script for RagerX compatible pools built with Python. Please refer to the [Pool Install Instructions](https://github.com/ragerxlol/ragerx-foss-install-instructions) for full details on how to start a RagerX pool.

## Design Theory

Payoutd is written as an independent Python script separate from the main pool API. This allows you to run it on a dedicated Linux user account if you choose to. It requires a connection to wallet-rpc, a daemon (can be remote), and the Postgres database.

This script pays out using PPLNS. It can handle normal, integrated, and subaddresses. Full accounting is preserved where the credits for each miner for each block are stored separately, in contrast to many other pools that store users' balance as a single field. Transaction malleability attacks are prevented by identifying each tx with a hash of its key images. As of now, completely failed payments are not retried, but require the pool operator to investigate why the transaction failed and manually mark the transaction as orphaned in the database. Once a transaction is marked as orphaned, a new payment will be attempted.

## Configuring Payoutd

Copy `config.example.json` to `config.json`. There are a few critical fields you must change;

```
{
  "general": {
    /* Interval in seconds that the main loop runs */
    "interval": 60,

    /* Interval in seconds to sleep if script cannot connect to wallet-rpc, daemon, or postgres */
    "self_test_timeout": 60,

    /* Number of network blocks to start checking blocks for orphan status */
    "block_orphan_depth": 10,

    /* Number of network blocks required to unlock credits */
    "block_mature_depth": 60,

    /* Path to write the PID of this script */
    "pidfile": "payoutd.pid"
  },

  "coin": {
    /* Array of prefixes for validating public addresses */
    /* [ Normal, Integrated, Subaddress ] */
    /* See cryptonote_config.h */
    "address_prefixes": [18, 19, 42]
  },

  "postgres": {
    "db_hostname": "127.0.0.1",
    "db_port": "5432",
    /* Fill out the following fields with PSQL credentials */
    "db_name": "",
    "db_username": "",
    "db_password": ""
  },

  "daemon": {
    /* Daemon RPC location, can be remote */
    "hostname": "127.0.0.1",
    "port": 18081
  },

  "wallet": {
    /* Wallet RPC location, should not be remote */
    "hostname": "127.0.0.1",
    "port": 18090,

    /* RPC auth method can be "config" or "file" */
    "rpc_auth_method": "config",

    /* If "file", then set the path to a file with contents username:password */
    "rpc_auth_file": "/path/to/rpc-pass",

    /* If "config", then set the RPC username and password here */
    "rpc_username": "username",
    "rpc_password": "password"
  },

  "payments": {
    /* Payments priority, 1 is default */
    "priority": 1,

    /* Max number of recipients in a single tx */
    "max_recipients": 15,

    /* Ring size to use for payments */
    "ring_size": 11,

    /* Adjust the estimated fee withheld from miners, 2 will double the estimated fee */
    /* Only the actual fee will be deducted from miners balances */
    "fee_adjustment_factor": 2,

    /* Interval of network blocks between payments */
    /* If network height % 20 === 0 then payments will be made */
    /* This allows full change to unlock between each payout */
    "network_block_interval": 20,

    /* Number of atomic units that the wallet's balance and the owed balance can differ */
    /* If this threshold is met, the script will throw a CriticalPaymentError and terminate */
    "warning_threshold": 100000000000,

    /* Maximum amount allowed to be paid to a single user in a payout */
    "max_payment_amount": 50000000000000
  },

  "fee": {
    /* The fee in % that payoutd will withhold */
    "percent": 3.5,

    /* Pool fees are credited to specific user accounts, and paid out as normal payments */
    /* You can define multiple user accounts to send fees to, as long as the total adds to 100 */
    /* The name field is purely for logging purposes, make sure to set the uid of the admin account */
    "split": [{
      "name": "dev",
      "uid": 1,
      "percent": 100
    }]
  },

  "logging": {
    /* directory to write logs to */
    "path": "logs",

    /* Each of the following can be "console", "file", or "both"
    "payoutd": "both",
    "daemon": "file",
    "wallet": "file"
  }

}
```

## Building and Development

Install dependencies:
```
sudo apt install python-pip python3-setuptools python3-distutils
pip install --user pipenv
```

Start the script:
```
~/.local/bin/pipenv install
~/.local/bin/pipenv shell
python main.py
```

### Contributing

Feel free to send PRs with improvements or other features.

### License

This code is released under the BSD-3-Clause license.
