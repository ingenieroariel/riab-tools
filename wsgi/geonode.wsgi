import site, os

site.addsitedir('/var/www/geonode/wsgi/geonode/lib/python2.6/site-packages')
os.environ['DJANGO_SETTINGS_MODULE'] = 'geonode.settings'

from django.core.handlers.wsgi import WSGIHandler
application = WSGIHandler()
