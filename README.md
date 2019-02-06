# service-watchdog
A Python script to monitor availability of a service (Linux)

The script was designed for RHEL\CentOS platforms as it uses systemctl.

# Functionality
The script is designed to monitor availability of a systemd service.
If the service is not running, the script tries to restart it.
The script keeps a log of its activities.
It notifies a user via email if an anomality is detected.

# To-do list
As the script is only a POC, it requires some changes to become fully production ready.
* Code refactoring
* Make it platform agnostic.
* Improve troubleshooting
* Create an installation script or write an Ansible module to deploy
* Add other logging options

# Installation
The script can be installed as systemd service using standard mechanism
1. Create a unit file
    `sudo vim /lib/systemd/system/watchdog.service`
    A template can be found in the repository
2. Set permissions
    `sudo chmod 644 /lib/systemd/system/watchdog.service`
3. Configure systemd
    reload systemd configuration
    `sudo systemctl daemon-reload`
    enable the service
    `sudo systemctl enable watchdog.service`
4. Start the service
    `sudo service watchdog start`

# Configuration
## The script has the following mandatory command line arguments:
* -config, c - a path to the script's configuration file(*.ini). A template is in the repository
* -service - a name of the service to monitor
* -email - an email address for notification
## Optional command line arguments
These parameters can be also specified in the configuration file.
If these arguments are specified in the command line, configuration file settings will be ignored.
If they are not specified in either location, the **script will fail**.
* --verify-interval', type=int, help='Time (in seconds) between service status checks
* --restart-interval', type=int, help='Time (in seconds) between attempts to restart the service if it is not running.
* --restart-limit', type=int, help='Maximum number of attempts to start the service

## Configuraion file
The templated is published in this repository.

# Logging
The script sends different type of messages to a file specified in the configuration file. Default: 
      `/var/log/service_watchdog.log` 
## Log messages examples:
```
06-Feb-19 21:48:38,454 root INFO Service lighttpd is running. The watchdog is going to sleep.
05-Feb-19 22:39:18,897 root INFO Service lighttpd was not recovered after the attempt to restart it. We need a pause(16s) before retry.
05-Feb-19 23:19:32,235 root INFO We had recovered the servive lighttpd after 2 tries.
```





