#Virtualenv setup

directory "/home/geonode/sites/" do
    owner "geonode"
    group "geonode"
    mode 0775
end

virtualenv "/home/geonode/sites/readthedocs.org" do
    owner "geonode"
    group "geonode"
    mode 0775
end

directory "/home/geonode/sites/readthedocs.org/run" do
    owner "geonode"
    group "geonode"
    mode 0775
end

git "/home/geonode/sites/readthedocs.org/checkouts/readthedocs.org" do
  repository "git://github.com/rtfd/readthedocs.org.git"
  reference "HEAD"
  user "geonode"
  group "geonode"
  action :sync
end

script "Install Requirements" do
  interpreter "bash"
  user "geonode"
  group "geonode"
  code <<-EOH
  /home/geonode/sites/readthedocs.org/bin/pip install -r /home/geonode/sites/readthedocs.org/checkouts/readthedocs.org/deploy_requirements.txt
  EOH
end

# Gunicorn setup

cookbook_file "/etc/init/readthedocs-gunicorn.conf" do
    source "gunicorn.conf"
    owner "root"
    group "root"
    mode 0644
    #notifies :restart, resources(:service => "readthedocs-gunicorn")
end

cookbook_file "/etc/init/readthedocs-celery.conf" do
    source "celery.conf"
    owner "root"
    group "root"
    mode 0644
    #notifies :restart, resources(:service => "readthedocs-celery")
end

service "readthedocs-gunicorn" do
    provider Chef::Provider::Service::Upstart
    enabled true
    running true
    supports :restart => true, :reload => true, :status => true
    action [:enable, :start]
end

service "readthedocs-celery" do
    provider Chef::Provider::Service::Upstart
    enabled true
    running true
    supports :restart => true, :reload => true, :status => true
    action [:enable, :start]
end


cookbook_file "/home/geonode/.bash_profile" do
    source "bash_profile"
    owner "geonode"
    group "geonode"
    mode 0755
end
