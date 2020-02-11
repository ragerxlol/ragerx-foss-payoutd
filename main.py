import os, sys, time, traceback, signal

from src.constants import *
from src.errors import *
from src import database, rpc, blocks, credit, payments, wallet, log

def self_test():
    if not database.check_connection():
        if not database.connection_init():
            return False
    if not rpc.check_rpc():
        return False
    return True


class Payoutd:
    kill_now = False
    def __init__(self):
        signal.signal(signal.SIGINT, self.exit_gracefully)
        signal.signal(signal.SIGTERM, self.exit_gracefully)
        signal.signal(signal.SIGHUP, self.handle_sighup)

    def exit_gracefully(self, signum, frame):
        self.kill_now = True

    def handle_sighup(self, signum, frame):
        log.open_log_files()


if __name__== "__main__":
    try:

        pid = os.getpid()
        pid_file = PID_FILE

        if os.path.isfile(pid_file):
            log.error("Payoutd is already running, exiting")
            os._exit(1)

        open(pid_file, 'w').write(str(pid))

        log.message('Payoutd initializing, python version: %s, pid: %d' % (sys.version, pid))
        payoutd = Payoutd()

        while not payoutd.kill_now:

            # newline for clarity
            log.message('')

            if not self_test():
                log.error('Failed self test, sleeping %s seconds...' % (PAYOUTD_SELF_TEST_TIMEOUT,))
                for i in range(PAYOUTD_SELF_TEST_TIMEOUT):
                    if payoutd.kill_now:
                        break
                    time.sleep(1)
                continue

            try:
                now = database.walltime_to_db_time(time.time())
                height = wallet.get_wallet_height()
                last_height = wallet.get_last_scan_height()

                log.message('Current height: %s / Last scan height: %s' % (height, last_height))
                if height == last_height:
                    log.message('No new blocks, sleeping for %s seconds...' % (PAYOUTD_TIMEOUT,))
                    for i in range(PAYOUTD_TIMEOUT):
                        if payoutd.kill_now:
                            break
                        time.sleep(1)
                    continue

                log.message('Checking for unlocked blocks')
                blocks.unlock_blocks()

                log.message('Calculating credits')
                credit.calculate()

                log.message('Unlocking credits')
                credit.unlock()

                if height % PAYMENTS_NETWORK_BLOCK_INTERVAL == 0:
                    log.message('Making payments')
                    payments.make_payments()

                log.message('Unlocking payments')
                payments.unlock()

                log.message('Setting last scan height to %s' % (height,))
                wallet.update_last_scan_height(height, now)

            except RecoverableError as e:
                log.error('Error during main loop, stopping until next run')
                log.error(e)

            if not payoutd.kill_now:
                log.message('Done, sleeping for %s seconds...' % (PAYOUTD_TIMEOUT,))
                for i in range(PAYOUTD_TIMEOUT):
                    if payoutd.kill_now:
                        break
                    time.sleep(1)

    except CriticalPaymentError:
        log.error('Critical payment error, halting payoutd')
        log.error(sys.exc_info())
        traceback.print_exception(*sys.exc_info())
        for i in range(31556952): # sleep for 1 year
            if payoutd.kill_now:
                break
            time.sleep(1)

    except:
        log.error('Exception:')
        log.error(sys.exc_info())
        traceback.print_exception(*sys.exc_info())

    finally:
        log.message('Payoutd ending')
        database.close_connection()
        if os.path.isfile(pid_file):
            os.unlink(pid_file)
        log.message('Bye!!!')
