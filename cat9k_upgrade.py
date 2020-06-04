from netmiko import ConnectHandler, FileTransfer
from datetime import datetime
from getpass import getpass
import difflib
from platform import system as system_name
from os import system as system_call
import sys

# ADJUST TO REQUIRED VALUES
target_version = '16.9.5'
image_filename = "imagetest.txt"
verification_commands = ['show run', 'show ip int br', 'show version']

def verify_version(ssh):
    show_version = ssh.send_command('show version')
    for line in show_version.splitlines():
        if line.startswith('Cisco IOS Software'):
            current_version = line.split(',')[2].split()[1]
    return current_version

def image_transfer(ssh, image_filename)
    with FileTransfer(ssh,source_file=image_filename,dest_file=image_filename) as scp_transfer:
        if scp_transfer.check_file_exists():
            print(f"File {image_filename} already exists on device.")
        else:
            if not scp_transfer.verify_space_available():
                raise ValueError("Insufficient free space available on device")
            else:
                print("Enabling SCP")
                scp_transfer.enable_scp()
                print("Transferring file...")
                scp_transfer.transfer_file()
                print("Disabling SCP")
                scp_transfer.disable_scp()

                print("Verifying file")
                if scp_transfer.verify_file():
                    print("File has been transferred correctly.")
                else:
                    raise ValueError("File was not trasferred correctly")

        # MD5
        local_md5 = scp_transfer.file_md5(image_filename)
        remote_md5 = scp_transfer.remote_md5(base_cmd='verify /md5')
        if local_md5 == remote_md5:
            print("Source and destination MD5 are the same")
        else:
            raise ValueError("MD5 failure between source and destination files")

def verify_boot(ssh):
    show_run_boot = ssh.send_command('show run | i boot system')
    if show_run_boot.split()[-1] == 'flash:packages.conf':
        print('BOOT statement is set correctly to packages.conf')
    else:
        print(f'BOOT statement is set incorrectly to {show_run_boot.split()[-1]}. Changing to packages.conf')
        ssh.send_config_set(['no boot system','boot system switch all flash:packages.conf'])

def ping(host):
    parameters = "-n 1" if system_name().lower() == "windows" else "-c 1"
    return system_call("ping " + parameters + " " + host + " > /dev/null") == 0

def wait_for_reboot(ip, repeat=500, delay=120):
    try:
        print(f'Waiting {delay} seconds for device to go down completely')
        time.sleep(delay)
        for i in range(repeat):
            if repeat % 60 == 0:
                print("Waiting {} more minutes for host to come online".format(delay / 60))
            ping_success = ping(ip)
            if ping_success:
                print ("Host is responding to pings again!")
                return True
        return False
    except KeyboardInterrupt:
        sys.exit(1)

device = input("Enter device IP address or Hostname: ")
username = input("Enter your username: ")
my_pass = getpass(prompt='Password: ')

device_parameters = {
    "device_type": "cisco_ios",
    "ip": device,
    "username": username,
    "password": my_pass,
    "secret": my_pass,
}

print(f"Logging in to {device}")
print(f">>> {datetime.now()}")

ssh = ConnectHandler(**device_parameters)
ssh.enable()

running_version = verify_version(ssh)

if running_version == target_version:
    raise ValueError(f'Device is running IOSXE {running_version} and does not require an upgrade')

# Collect show commands
pre_checks = [(ssh.send_command(command)).splitlines() for command in verification_commands]

image_transfer(ssh,image_filename)
print(f">>> {datetime.now()}")
verify_version(ssh)
print(f">>> {datetime.now()}")

print("Writing memory!")
ssh.send_command('wr mem')
print('Installing new software!')
ssh.send_command_expect(f'install add file flash:{image_filename} activate commit')
ssh.send_command('Y')

# Wait for device to come back
if wait_for_reboot():
    ssh = ConnectHandler(**device_parameters)
    ssh.enable()

# Collect show commands
post_checks = [(ssh.send_command(command)).splitlines() for command in verification_commands]

with open(f'{device}.html', 'w') as diff_file:
    diff = difflib.HtmlDiff()
    diff_file.write(diff.make_file(pre_checks,post_checks,fromdesc='PreCheck', todesc='PostCheck'))


