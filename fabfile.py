# easy_install fabric
#
# Usage:
#     fab -H user@hostname geonode_dev
#         -- or --
#     fab -H user@hostname geonode_prod
#         -- or --
#     fab -H user@hostname geonode_release
#         -- or --
#     fab -H user@hostname create_ami 

import os
import datetime

from fabric.api import env, sudo, run, cd, local, put
from fabric.contrib.project import rsync_project

AWS_USER_ID=os.environ['AWS_USER_ID']
AWS_ACCESS_KEY_ID=os.environ['AWS_ACCESS_KEY_ID']
AWS_SECRET_ACCESS_KEY=os.environ['AWS_SECRET_ACCESS_KEY']
KEY_BASE=os.environ['EC2_KEY_BASE']
KEY_PATH='~/.ssh/' # trailing slash please
RELEASE_BUCKET = 'geonode-release'
AMI_BUCKET = 'geonode-ami-dev'
ARCH='i386'
MAKE_PUBLIC=True
RELEASE_PKG_URL='https://s3.amazonaws.com/geonode-release/GeoNode-1.0.1-2011-03-04.tar.gz'
RELEASE_NAME='GeoNode-1.0.1-2011-03-04.tar.gz'
VERSION='1.0.1'
#RELEASE_PKG_URL='http://dev.geonode.org/release/GeoNode-1.0.tar.gz'
#RELEASE_NAME='GeoNode-1.0.tar.gz'
#VERSION='1.0'
POSTGRES_USER='geonode'
POSTGRES_PASSWORD='g30n0d3'
ADMIN_USER='admin' # Should not be modified
ADMIN_PASSWORD='adm1n'
ADMIN_EMAIL='admin@admin.admin'
ENABLE_FTP=False

# Geonode build

def upgrade():
    sudo('apt-get -y dist-upgrade')

def sunjava():
    sudo('export DEBIAN_FRONTEND=noninteractive')
    sudo('add-apt-repository "deb http://archive.canonical.com/ lucid partner"')
    sudo('apt-get -y update')
    # 'Accept' SunOracle Licensing
    sudo('echo "sun-java6-bin shared/accepted-sun-dlj-v1-1 boolean true" | sudo debconf-set-selections')
    sudo('echo "sun-java6-jdk shared/accepted-sun-dlj-v1-1 boolean true" | sudo debconf-set-selections')
    sudo('echo "sun-java6-jre shared/accepted-sun-dlj-v1-1 boolean true" | sudo debconf-set-selections')
    sudo('echo "sun-java6-jre sun-java6-jre/stopthread boolean true" | sudo debconf-set-selections')
    sudo('echo "sun-java6-jre sun-java6-jre/jcepolicy note" | sudo debconf-set-selections')
    sudo('echo "sun-java6-bin shared/present-sun-dlj-v1-1 note" | sudo debconf-set-selections')
    sudo('echo "sun-java6-jdk shared/present-sun-dlj-v1-1 note" | sudo debconf-set-selections')
    sudo('echo "sun-java6-jre shared/present-sun-dlj-v1-1 note" | sudo debconf-set-selections')
    sudo("apt-get install -y --force-yes sun-java6-jdk")

def openjdk():
    sudo('apt-get install -y openjdk-6-jdk')   

def setup():
    sudo('apt-get -y update')
    sudo('apt-get install -y python-software-properties')
    # upgrade()

    # Choose one between sunjava and openjdk.
    #openjdk()
    sunjava()

    sudo('apt-get install -y zip subversion git-core binutils build-essential python-dev python-setuptools python-imaging python-reportlab gdal-bin libproj-dev libgeos-dev unzip maven2 python-urlgrabber libpq-dev')

def setup_pgsql(setup_geonode_db=True):
    sudo("apt-get install -y postgresql-8.4 libpq-dev python-psycopg2")
    # ToDo: Add postgis support
    # update pg_hba.conf to allow for md5 local connections
    db_exists = int(sudo("psql -qAt -c \"select count(*) from pg_catalog.pg_database where datname = 'geonode'\"", user="postgres"))
    if(setup_geonode_db):
        if(db_exists > 0):
            sudo("dropdb geonode", user="postgres")
            sudo("dropuser geonode", user="postgres")
        sudo("createuser -SDR geonode", user="postgres")
        sudo("createdb -O geonode geonode", user="postgres")
        sudo("psql -c \"alter user geonode with encrypted password '%s'\" " % (POSTGRES_PASSWORD), user="postgres")

def setup_prod():
    setup_pgsql(True)
    sudo("apt-get install -y tomcat6 libjpeg-dev libpng-dev python-gdal apache2 libapache2-mod-wsgi")
    # -Xms1024m -Xmx1024m -XX:NewSize=256m -XX:MaxNewSize=256m -XX:PermSize=256m -XX:MaxPermSize=256m

def build():
    run('git clone git://github.com/GeoNode/geonode.git')
    #run('git clone git://github.com/jj0hns0n/geonode.git')
    run('cd geonode;git submodule update --init')
    # WORKAROUND: Avoid compiling reportlab because it is already installed via apt-get and it hangs with fabric (too much data)
    run("sed '/reportlab/d' geonode/shared/core-libs.txt > core-libs.txt;mv core-libs.txt geonode/shared/core-libs.txt")
    run('cd geonode;python bootstrap.py')
    run('cd geonode;source bin/activate; paver build')
    run('cd geonode;source bin/activate; paver make_release')

def switch_branch(branch_name):
    run('cd geonode;git reset --hard')
    run('cd geonode;git checkout %s' % branch_name)
    run('cd geonode;source bin/activate;pip install -r shared/core-libs.txt')
    run('cd geonode;cp src/GeoNodePy/geonode/sample_local_settings.py src/GeoNodePy/geonode/local_settings.py')
    run('cd geonode;source bin/activate;django-admin.py syncdb --settings=geonode.settings')
    run('cd geonode;source bin/activate; paver make_release')

def upload_release():
    put('./upload.py', '~/')
    release_file = str(run('ls ~/geonode/shared/GeoNode*.tar.gz'))
    run('cd geonode/shared;export AWS_ACCESS_KEY_ID=%s;export AWS_SECRET_ACCESS_KEY=%s;python ~/upload.py %s %s' % (AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY,RELEASE_BUCKET,release_file)) 
    run('rm ~/upload.py')
    return release_file

def deploy_dev():
    run("perl -pi -e 's/127.0.0.1/0.0.0.0/g' geonode/shared/dev-paste.ini")
    run("perl -pi -e 's/localhost/0.0.0.0/g' geonode/src/geoserver-geonode-ext/jetty.xml")
    run('echo "SITEURL = \'http://%s:8000/\'" >> geonode/src/GeoNodePy/geonode/local_settings.py' % env.host )
    run('echo "GEOSERVER_BASE_URL = \'http://%s:8001/geoserver/\'" >> geonode/src/GeoNodePy/geonode/local_settings.py' % env.host )
    run('echo "GEONETWORK_BASE_URL = \'http://%s:8001/geonetwork/\'" >> geonode/src/GeoNodePy/geonode/local_settings.py' % env.host )
    # set the django settings module in the activate script to avoid having to type in some cases
    run('echo "export DJANGO_SETTINGS_MODULE=\'geonode.settings\'" >> geonode/bin/activate')
    # create a passwordless superuser, you can use 'django-admin.py changepassword admin' afterwards
    run('cd geonode;source bin/activate;django-admin.py createsuperuser --noinput --username=%s --email=%s' % (ADMIN_USER, ADMIN_EMAIL))
    print "In order to login you have to run first 'django-admin.py changepassword admin'"

def hosty():
    print "Access your new geonode instance via the following url:"
    print "http://%s:8000" % env.host
    run('cd geonode;source bin/activate;paver host')

def deploy_prod(host=None):
    x86_64 = False
    uname = sudo('uname -a')
    if("x86_64" in uname):
        x86_64 = True
    if(host is None):
        host = env.host
    sudo('export DEBIAN_FRONTEND=noninteractive')
    if(x86_64 == False):
        sudo('add-apt-repository "deb http://apt.opengeo.org/lucid lucid main"')
        sudo('apt-get -y update')
    sudo('echo "geonode geonode/django_user string %s" | sudo debconf-set-selections' % ADMIN_USER)
    sudo('echo "geonode geonode/django_password password %s" | sudo debconf-set-selections' % ADMIN_PASSWORD)
    sudo('echo "geonode geonode/hostname string %s" | sudo debconf-set-selections' % host)
    if(x86_64 == False):
        sudo("apt-get install -y --force-yes geonode")
    else:
        sudo("wget http://apt.opengeo.org/lucid/pool/main/g/geonode/geonode_1.0.final+1_i386.deb")
        sudo("dpkg --force-architecture -i geonode_1.0.final+1_i386.deb")

def setup_geonode_wsgi(host):
    run('mkdir -p ~/wsgi')
    put('./wsgi/*', '~/wsgi/')
    run("perl -pi -e 's/replace.me.site.url/%s/g' ~/wsgi/geonode" % host)
    sudo("cp ~/wsgi/geonode /etc/apache2/sites-available/")
    sudo("cp ~/wsgi/geonode.wsgi /var/www/geonode/wsgi/")
    sudo("a2ensite geonode")
    sudo("a2dissite default")
    sudo("a2enmod proxy_http")
    sudo("/etc/init.d/apache2 restart")
    run('rm -rf ~/wsgi')

def install_release(host=None):
    if(host == None):
        host = env.host
    sudo('apt-get install -y zip')
    run('rm -rf ~/deploy')
    run('mkdir ~/deploy')
    put('./deploy/*', '~/deploy/')
   
    #try:
    #    run('cp /var/www/geonode/wsgi/geonode/src/GeoNodePy/geonode/local_settings.py ~/deploy')
    #except:
    #    pass

    run('rm -rf ~/release')
    run('mkdir ~/release')
    run('wget %s -O ~/release/%s' % (RELEASE_PKG_URL, RELEASE_NAME))
    run('chmod +x ~/deploy/deploy.sh')
    run("perl -pi -e 's/replace.me.site.url/%s/g' ~/deploy/deploy.local.sh" % host) 
    run('cp ~/deploy/sample_local_settings.py ~/deploy/local_settings.py')
    run("perl -pi -e 's/replace.me.site.url/%s/g' ~/deploy/local_settings.py" % host) 
    run("perl -pi -e 's/replace.me.pg.user/%s/g' ~/deploy/local_settings.py" % POSTGRES_USER) 
    run("perl -pi -e 's/replace.me.pg.pw/%s/g' ~/deploy/local_settings.py" % POSTGRES_PASSWORD) 
    sudo("mkdir -p /var/www/geonode/wsgi/geonode")
    # Google API Key / SMTP Settings
    sudo('~/deploy/deploy.sh ~/release/%s' % (RELEASE_NAME))
    
    # createsuperuser / changepassword
    sudo('echo "export DJANGO_SETTINGS_MODULE=\'geonode.settings\'" >> /var/www/geonode/wsgi/geonode/bin/activate')
    sudo('cd /var/www/geonode/wsgi/geonode;source bin/activate;django-admin.py createsuperuser --noinput --username=%s --email=%s' % (ADMIN_USER, ADMIN_EMAIL))
    put('changepw.py', '~/')
    run("perl -pi -e 's/replace.me.admin.user/%s/g' ~/changepw.py" % ADMIN_USER) 
    run("perl -pi -e 's/replace.me.admin.pw/%s/g' ~/changepw.py" % ADMIN_PASSWORD) 
    sudo('cd /var/www/geonode/wsgi/geonode;source bin/activate;cat ~/changepw.py | django-admin.py shell')
    run('rm ~/changepw.py')
    run('rm -rf ~/release')
    run('rm -rf ~/deploy')
  
    setup_geonode_wsgi(host)


def setup_batch_upload(internal_ip=None):
    run('mkdir ~/celery')
    put('./celery/*', '~/celery/')
    sudo("chown root:root /home/ubuntu/celery/celeryd")
    sudo("chmod 0700 /home/ubuntu/celery/celeryd") 
    sudo("mv /home/ubuntu/celery/celeryd /etc/init.d")
    sudo("mv /home/ubuntu/celery/celeryd-default /etc/default/celeryd")
    sudo("update-rc.d celeryd defaults")
    sudo("/etc/init.d/celeryd start")
    run("rm -rf ~/celery")
    sudo("perl -pi -e 's/false/true/g' /var/lib/tomcat6/webapps/geoserver-geonode-dev/data/ftp.xml")
    if(internal_ip == None):
        internal_ip = run("curl http://169.254.169.254/latest/meta-data/local-ipv4")
    sudo('echo "GEOSERVER_IP_WHITELIST = [\'127.0.0.1\',\'%s\']" >> /var/www/geonode/wsgi/geonode/src/GeoNodePy/geonode/local_settings.py' % internal_ip )
    sudo("/etc/init.d/tomcat6 restart")
    sudo("/etc/init.d/apache2 restart")

def setup_deb():
    sudo('apt-get -y update')
    sudo('echo "postfix postfix/main_mailer_type    select  No configuration" | sudo debconf-set-selections')
    sudo('echo "postfix postfix/mailname    string  localhost" | sudo debconf-set-selections')
    sudo('apt-get install -y debhelper devscripts')
    run('mkdir -p geonode-deb')
    rsync_project('~/geonode-deb/', './deb/debian')

def geonode_dev():
    setup()
    build()
    deploy_dev()
    #hosty()

def geonode_prod():
    setup()
    setup_prod()
    deploy_prod()

def geonode_release():
    setup()
    setup_prod()
    install_release()

def geonode_deb():
    setup_deb()
    run('wget %s -O ~/geonode-deb/%s' % (RELEASE_PKG_URL, RELEASE_NAME))
    run('cd geonode-deb; tar xvf %s' % RELEASE_NAME)
    run('cd geonode-deb; debuild -uc -us')

def install_ec2_tools():
    sudo('export DEBIAN_FRONTEND=noninteractive')
    sudo('add-apt-repository "deb http://us.archive.ubuntu.com/ubuntu/ lucid multiverse"')
    sudo('add-apt-repository "deb-src http://us.archive.ubuntu.com/ubuntu/ lucid multiverse"')
    sudo('add-apt-repository "deb http://us.archive.ubuntu.com/ubuntu/ lucid-updates multiverse"')
    sudo('add-apt-repository "deb-src http://us.archive.ubuntu.com/ubuntu/ lucid-updates multiverse"')
    sudo('apt-get -y update')
    sudo('apt-get install -y ec2-ami-tools')
    sudo('apt-get install -y ec2-api-tools')

def cleanup_temp():
    # ToDo: Update as necessary
    sudo("rm -f /root/.*hist* $HOME/.*hist*")
    sudo("rm -f /var/log/*.gz")

def copy_keys():
    sudo('rm -f ~/.ssh/*%s.pem' % (KEY_BASE))
    put(('%s*%s*' % (KEY_PATH, KEY_BASE)), '~/.ssh/', mode=0400)
    pass

def create_ami():
    #setup()
    #setup_prod()
    #deploy_prod(host='replace.me.host')
    #install_release(host='replace.me.host')
    #setup_batch_upload(internal_ip='replace.me.internal')
    cleanup_temp()
    copy_keys()
    put('./update-instance', '~/')
    sudo('mv /home/ubuntu/update-instance /etc/init.d')
    sudo('chmod +x /etc/init.d/update-instance')
    sudo('sudo update-rc.d -f update-instance start 20 2 3 4 5 .')
    install_ec2_tools()
    sudo('export AWS_USER_ID=%s' % AWS_USER_ID)
    sudo('export AWS_ACCESS_KEY_ID=%s' % AWS_ACCESS_KEY_ID)
    sudo('export AWS_SECRET_ACCESS_KEY=%s' % AWS_SECRET_ACCESS_KEY)
    #ToDo Support various combos of arch/base-ami 
    sudo('export ARCH=%s' % ARCH) 
    prefix = 'geonode-%s-%s' % (VERSION, datetime.datetime.now().strftime('%Y%m%d%H%M%S'))
    excludes = '/mnt,/root/.ssh,/home/ubuntu/.ssh,/tmp'
    sudo("ec2-bundle-vol -r %s -d /mnt -p %s -u %s -k ~/.ssh/pk-*.pem -c ~/.ssh/cert-*.pem -e %s" % (ARCH, prefix, AWS_USER_ID, excludes))
    sudo("ec2-upload-bundle -b %s -m /mnt/%s.manifest.xml -a %s -s %s" % (AMI_BUCKET, prefix, AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY))
    output = sudo('ec2-register --name "%s/%s" "%s/%s.manifest.xml" -K ~/.ssh/pk-*.pem -C ~/.ssh/cert-*.pem' % (AMI_BUCKET, prefix, AMI_BUCKET, prefix)) 
    ami_id = output.split('\t')[1]
    if MAKE_PUBLIC:
        sudo("ec2-modify-image-attribute -l -a all -K ~/.ssh/pk-*.pem -C ~/.ssh/cert-*.pem %s" % (ami_id))
    print "AMI %s Ready for Use" % (ami_id)


# Chef stuff

env.chef_executable = '/var/lib/gems/1.8/bin/chef-solo'

def install_chef():
    sudo('apt-get update', pty=True)
    sudo('apt-get install -y git-core rubygems ruby-full ruby-dev', pty=True)
    sudo('gem install chef --no-ri --no-rdoc', pty=True)

def sync_config():
    local('rsync -av -e "ssh -o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no -i %s" . %s:chef' % (env.key_filename[0],env.host_string))
    sudo('rsync -av chef /etc/')

def update():
    sync_config()
    run('cd /etc/chef;sudo %s' % env.chef_executable, pty=True)

def reload():
    "Reload the server."
    env.user = "docs"
    run("kill -HUP `cat %s/gunicorn.pid`" % env.rundir, pty=True)

def restart():
    "Restart (or just start) the server"
    #sudo('restart readthedocs-gunicorn', pty=True)
