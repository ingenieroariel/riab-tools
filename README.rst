=========
Chef GeoNode 
=========

Summary
==================
Chef GeoNode is a set of scripts (recipes, cookbooks, fabric and whatnot) for launching GeoNode instances on ec2 or other infrastructure.

Requirements
==================
* aws (http://aws.amazon.com/)
 - download geonode.pem from web interface
 - export AWS_ACCESS_KEY_ID='blahblah'
 - export AWS_SECRET_ACCESS_KEY='blebleble'
* boto (http://code.google.com/p/boto/)
 - easy_install boto 
* fabric (http://docs.fabfile.org/0.9.3/)
 - easy_install fabric
* chef (http://opscode.com/chef)
 - gem install chef

Usage 
==================
* ec2.py launch
* fab -i geonode.pem -H user@host geonode_dev
* fab -i geonode.pem -H user@host geonode_prod
* fab -i geonode.pem -H user@host install_chef 
* fab -i geonode.pem -H user@host sync_config
* fab -i geonode.pem -H user@host update 
