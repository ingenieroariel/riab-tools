# easy_install boto 
# You will also need:
# - A .pem keyfile generated using the Amazon web interface to create new instances
# - The secret and access keys created from the 
# The only pre-reqs are having created a keypair (.pem file) 
# via the amazon web interface and knowing the AWS key and secret
#
# Usage:
#     export AWS_ACCESS_KEY_ID='blahblah'
#     export AWS_SECRET_ACCESS_KEY='blebleble'
#     ec2.py create
import os, time, boto
import sys
import ConfigParser

CONFIG_FILE=".gnec2.cfg"



MAVERIK_64="ami-688c7801"
MAVERIK_32="ami-1a837773"
LUCID_64="ami-da0cf8b3"
LUCID_32="ami-a403f7cd"

def writeconfig(config):
    # Writing our configuration file to CONFIG_FILE
    configfile = open(CONFIG_FILE, 'wb')
    config.write(configfile)
    configfile.close()
 
def readconfig():

    config = ConfigParser.RawConfigParser()

    # If there is no config file, let's write one.
    if not os.path.exists(CONFIG_FILE):
        config.add_section('ec2')
        config.set('ec2', 'AMI', LUCID_32)
        config.set('ec2', 'INSTANCE_TYPE', 'm1.small')
        config.set('ec2', 'SECURITY_GROUP', 'geonode')
        config.set('ec2', 'KEY_PATH', 'geonode.pem')
        config.set('ec2', 'USER', 'ubuntu')
        writeconfig(config)
    else:
        config.read(CONFIG_FILE)
    return config

def create():
    config = readconfig()
    MY_AMI=config.get('ec2', 'AMI')
    SECURITY_GROUP=config.get('ec2', 'SECURITY_GROUP')
    KEY_PATH = config.get('ec2', 'KEY_PATH')
    INSTANCE_TYPE = config.get('ec2', 'INSTANCE_TYPE')

    create = True

    if config.has_option('ec2', 'HOST'):
        host = config.get('ec2', 'HOST')
        if host != "" and host is not None:
            print "there is already an instance created"
            create = False
            return
 
    if create:
        conn = boto.connect_ec2()
        image = conn.get_image(MY_AMI)
        security_groups = conn.get_all_security_groups()

        try:
            [geonode_group] = [x for x in security_groups if x.name == SECURITY_GROUP]
        except ValueError:
            # this probably means the security group is not defined
            # create the rules programatically to add access to ports 22, 80, 8000 and 8001
            geonode_group = conn.create_security_group(SECURITY_GROUP, 'Cool GeoNode rules')
            geonode_group.authorize('tcp', 21, 21, '0.0.0.0/0') # Batch Upload FTP
            geonode_group.authorize('tcp', 22, 22, '0.0.0.0/0') # SSH
            geonode_group.authorize('tcp', 80, 80, '0.0.0.0/0') # Apache
            geonode_group.authorize('tcp', 2300, 2400, '0.0.0.0/0') # Passive FTP 
            geonode_group.authorize('tcp', 8000, 8001, '0.0.0.0/0') # Dev Django and Jetty
            geonode_group.authorize('tcp', 8021, 8021, '0.0.0.0/0' ) # Batch Upload FTP
            geonode_group.authorize('tcp', 8080, 8080, '0.0.0.0/0' ) # Tomcat

        try:
            [geonode_key] = [x for x in conn.get_all_key_pairs() if x.name == 'geonode']
        except ValueError:
            # this probably means the key is not defined
            # get the first one in the belt for now:
            print "GeoNode file not found in the server"
            geonode_key = conn.get_all_key_pairs()[0]

        reservation = image.run(security_groups=[geonode_group,], key_name=geonode_key.name, instance_type=INSTANCE_TYPE)
        instance = reservation.instances[0]

        print "Firing up instance"

        # Give it 10 minutes to appear online
        for i in range(120):
            time.sleep(5)
            instance.update()
            print instance.state
            if instance.state == "running":
                break

        if instance.state == "running":
            dns = instance.dns_name
            print "Instance up and running at %s" % dns

        config.set('ec2', 'HOST', dns)
        config.set('ec2', 'INSTANCE', instance.id)
        writeconfig(config)

        print "ssh -i %s ubuntu@%s" % (KEY_PATH, dns)
        print "Terminate the instance via the web interface %s" % instance

        time.sleep(20)
 
def terminate():
    config = readconfig()
    instance_id = config.get('ec2', 'INSTANCE')
    conn = boto.connect_ec2()
    conn.get_all_instances()
    instance = None
    for reservation in conn.get_all_instances():
        for ins in reservation.instances:
            if ins.id == instance_id:
                instance = ins

    print 'Terminating instance'
    instance.terminate()
    # Give it 10 minutes to terminate
    for i in range(120):
        time.sleep(5)
        instance.update()
        print instance.state
        if instance.state == "terminated":
            config.set('ec2', 'HOST', '')
            config.set('ec2', 'INSTANCE', '')
            configfile = open(CONFIG_FILE, 'wb')
            config.write(configfile)
            configfile.close()
            break

if sys.argv[1] == "create":
    create()
elif sys.argv[1] == "terminate":
    terminate()
elif sys.argv[1] == "host":
    config = readconfig()
    print config.get('ec2', 'HOST')
elif sys.argv[1] == "key":
    config = readconfig()
    print config.get('ec2', 'KEY_PATH')
else:
    print "Usage:\n    python %s create\n    python %s terminate" % (sys.argv[0], sys.argv[0])

