import os
import subprocess
import argparse
import time
import datetime
import logging
import smtplib
import configparser
#logging.basicConfig(format='%(process)d-%(levelname)s-%(message)s')
#from argparse import ArgumentParser
parser = argparse.ArgumentParser(description='Processing input parameters')
parser.add_argument('-config', '-c', help='Path to the configuration file', required=True)
parser.add_argument('-service', help='Name of the service to be checked', required=True)
parser.add_argument('-email', help='Email of address for the notification', required=True)
parser.add_argument('--verify-interval', type=int, help='Time (in seconds) between service status checks')
parser.add_argument('--restart-interval', type=int, help='Time (in seconds) between attempts to restart the service if it is not running.')
parser.add_argument('--restart-limit', type=int, help='Maximum number of attempts to start the service')
try:
    args = vars(parser.parse_args())
except:
    raise

service = args["service"]
config_file = args["config"]
verify_interval = args["verify_interval"]
restart_interval = args["restart_interval"]
restart_limit = args["restart_limit"]
email_address = args["email"]

config =  configparser.ConfigParser()
try:
    config.read(config_file)
except:
    raise

#configure logging to a file specified in the config file
logging.basicConfig(filename=config["MISC"]["log_file"],
                            filemode='a',
                            format='%(asctime)s,%(msecs)d %(name)s %(levelname)s %(message)s',
                            datefmt='%d-%b-%y %H:%M:%S',
                            level=logging.DEBUG)
logging.info(f"The watchdog has started. Arguments:{args}")

#we read the configuration file. If a parameter specified as a command line argument, we will ignore the setting in the configuration file
try:
    if verify_interval == None:
        verify_interval = int(config["VERIFICATION"]["verify_interval"])
    if restart_interval == None:
        restart_interval = int(config["VERIFICATION"]["restart_interval"])
    if restart_limit == None:
        restart_limit = int(config["VERIFICATION"]["restart_limit"])

except:
    logging.error("Cannot assign an input parameter",exc_info=True)
    raise


class ProcessRecoveryStatus(object):
    name = ""
    start_time = ""
    end_time = ""
    attempts = 0
    status = ""

#get the service
def get_service_status(name):
    process = subprocess.Popen(['service', name, 'status'], stdout=subprocess.PIPE)
    (output, err) = process.communicate()
    output = output.decode('utf-8')
    if process.returncode == 0:
        #service exist
        if "active (running)" in output:
            service_status = "Running"
        elif "inactive (dead)" in output:
            service_status = "NotRunning"
        else:
            service_status = "Other"
    elif process.returncode == 3:
        if "Active: failed" in output:
            service_status = "Failed"
        else:
            service_status = "NotRunning"
    elif process.returncode == 4:
        service_status = "NotFound"
    else:
        service_status = "Other"
    return service_status

def restart_service_once(name):
    logging.info(f'Service {name} will be restarted')
    process = subprocess.Popen(['service', name, 'restart'], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    return process
    #(output, err) = process.communicate()

def restart_service(name, restart_interval, restart_limit):
    status = ProcessRecoveryStatus()
    status.attempts = 0
    status.start_time = datetime.datetime.today()
    status.name = name
    status.status = "dead"
    is_running = False
    while ((status.attempts < restart_limit) and (is_running == False)):
        status.attempts+=1
        restart_service_once(name)
        if get_service_status(name) == "Running":
            is_running = True
        else:
            logging.info(f'Service {name} was not recovered after the attempt to restart it. We need a pause({restart_interval}s) before retry.')
            time.sleep(restart_interval)
    if is_running == False:
        logging.error(f'We were not able to recover the service {name} after {restart_limit} tries.')
        status.status = "dead"
        status.end_time = datetime.datetime.today()
        return status
    else:
        logging.info(f'We had recovered the servive {name} after {status.attempts} tries.')
        status.status = "alive"
        status.end_time = datetime.datetime.today()
        return status
def send_notification_email(email_address, message):
    #improvement: add email module support (to fill subject etc)
    try:
        smtp_server = smtplib.SMTP(config["SMTP_SERVER"]["smtp_server_address"], config["SMTP_SERVER"]["smtp_server_port"])
        smtp_server.starttls()
        smtp_server.login(config["SMTP_SERVER"]["smtp_server_login"], config["SMTP_SERVER"]["smtp_password"])
        smtp_server.sendmail(config["SMTP_SERVER"]["email_from"],email_address,message)
        smtp_server.quit()
        logging.info("A notification email was sent")
    except:
        logging.error("Cannot send an email",exc_info=True)
        raise
def watchdog_master(service,restart_interval, restart_limit,verify_interval,email):
    #the function controls the service verification function
    is_service_healthy = True
    while is_service_healthy == True:
        if get_service_status(service) == "Running":
            logging.info(f'Service {service} is running. The watchdog is going to sleep.')
            time.sleep(verify_interval)
        else:
            logging.warning(f'Service {service} is NOT running. We will try to recover it')
            #try to restart the service
            service_recovery_status = restart_service(service,restart_interval, restart_limit)
            if service_recovery_status.status == "alive":
                logging.info(f'Service {service} was recovered.')
                notification_email_body = f'Service {service} was recovered.'
                notification_email_body = notification_email_body + "\n" + f"Degradation started at: {service_recovery_status.start_time}"
                notification_email_body = notification_email_body + "\n" + f"The service was recovered at: {service_recovery_status.end_time}"
                notification_email_body = notification_email_body + "\n" + f"Numbers of attempts to recover: {service_recovery_status.attempts}"
                is_service_healthy = True
                try:
                    send_notification_email(email,notification_email_body)
                except:
                    logging.error("We were not able to send an email but we continue the script running")
            else:
                logging.error(f'Service {service} was not recovered. we will notify the master')
                logging.info(f'Service {service} was recovered.')
                notification_email_body = f'Service {service} is down.'
                notification_email_body = notification_email_body + "\n" + f"Degradation started at: {service_recovery_status.start_time}"
                notification_email_body = notification_email_body + "\n" + f"The recovery process was stopped: {service_recovery_status.end_time}"
                notification_email_body = notification_email_body + "\n" + f"Numbers of attempts to recover: {service_recovery_status.attempts}"
                send_notification_email(email,notification_email_body)
                is_service_healthy = False
  

watchdog_master(service,restart_interval, restart_limit,verify_interval, email_address)
logging.info("The script has been completed")