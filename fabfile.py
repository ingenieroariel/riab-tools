# easy_install fabric
#
# Usage:
#     fab -H user@hostname geonode_dev
#         -- or --
#     fab -H user@hostname geonode_prod

from fabric.api import env, sudo, run, cd, local

# Geonode build

def upgrade():
    sudo('apt-get -y dist-upgrade')

def sunjava():
    sudo('add-apt-repository "deb http://archive.canonical.com/ lucid partner"')
    sudo('apt-get -y update')
    sudo("apt-get install -y sun-java6-jdk")

def openjdk():
    sudo('apt-get install -y openjdk-6-jdk')   

def setup():
    sudo('apt-get -y update')
    # upgrade()

    # Choose one between sunjava and openjdk. If it is an automatic installation sun java cannot be used because it expects user input.
    openjdk()  # or sunjava()

    sudo('apt-get install -y subversion git-core binutils build-essential python-dev python-setuptools python-imaging python-reportlab gdal-bin libproj-dev libgeos-dev unzip maven2 python-urlgrabber')

def build():
    run('git clone git://github.com/GeoNode/geonode.git')
    run('cd geonode;git submodule update --init')
    # WORKAROUND: Avoid compiling reportlab because it is already installed via apt-get and it hangs with fabric (too much data)
    run("sed '/reportlab/d' geonode/shared/core-libs.txt > core-libs.txt;mv core-libs.txt geonode/shared/core-libs.txt")
    run('cd geonode;python bootstrap.py')
    run('cd geonode;source bin/activate; paver build')
    run('cd geonode;source bin/activate; paver make_release')

def deploy_dev():
    run("perl -pi -e 's/127.0.0.1/0.0.0.0/g' geonode/shared/dev-paste.ini")
    run("perl -pi -e 's/localhost/0.0.0.0/g' geonode/src/geoserver-geonode-ext/jetty.xml")
    run('echo "SITEURL = \'http://%s:8000/\'" >> geonode/src/GeoNodePy/geonode/local_settings.py' % env.host )
    run('echo "GEOSERVER_BASE_URL = \'http://%s:8001/geoserver/\'" >> geonode/src/GeoNodePy/geonode/local_settings.py' % env.host )
    run('echo "GEONETWORK_BASE_URL = \'http://%s:8001/geonetwork/\'" >> geonode/src/GeoNodePy/geonode/local_settings.py' % env.host )
    # set the django settings module in the activate script to avoid having to type in some cases
    run('echo "export DJANGO_SETTINGS_MODULE=\'geonode.settings\'" >> geonode/bin/activate')
    # create a passwordless superuser, you can use 'django-admin.py changepassword admin' afterwards
    run('cd geonode;source bin/activate;django-admin.py createsuperuser --noinput --username=admin --email=admin@admin.admin')
    print "In order to login you have to run first 'django-admin.py changepassword admin'"

def hosty():
    print "Access your new geonode instance via the following url:"
    print "http://%s:8000" % env.host
    run('cd geonode;source bin/activate;paver host')

def deploy_prod():
    sudo('export DEBIAN_FRONTEND=noninteractive')
    sudo('add-apt-repository "deb http://apt.opengeo.org/lucid lucid main"')
    sudo('apt-get -y update')
    sudo('echo "geonode geonode/django_user string admin" | sudo debconf-set-selections')
    sudo('echo "geonode geonode/django_password password adm1n" | sudo debconf-set-selections')
    sudo('echo "geonode geonode/hostname string %s" | sudo debconf-set-selections' % env.host)
    sudo("apt-get install -y --force-yes geonode")

def geonode_dev():
    setup()
    build()
    deploy_dev()
    hosty()

def geonode_prod():
    setup()
    deploy_prod()

# Chef stuff

env.chef_executable = '/var/lib/gems/1.8/bin/chef-solo

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
