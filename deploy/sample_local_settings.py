DEBUG = TEMPLATE_DEBUG = False
MINIFIED_RESOURCES = True
SERVE_MEDIA = False

SITENAME = "GeoNode"
SITEURL = "http://replace.me.site.url/"

# sqlite
#DATABASE_NAME = '/var/www/geonode/wsgi/geonode/production.db'

# postgres
DATABASE_ENGINE = 'postgresql_psycopg2'
DATABASE_NAME = 'geonode'
DATABASE_USER = 'replace.me.pg.user'
DATABASE_PASSWORD = "replace.me.pg.pw"
DATABASE_HOST = 'localhost'
DATABASE_PORT = '5432'

LANGUAGE_CODE = 'en'

MEDIA_ROOT = '/var/www/geonode/htdocs/media/'
MEDIA_URL = SITEURL + 'media/'
ADMIN_MEDIA_PREFIX = '/static/admin-media-files/'

GEONODE_UPLOAD_PATH = '/var/www/geonode/htdocs/media/'
GEONODE_CLIENT_LOCATION = SITEURL 
DEFAULT_LAYERS_OWNER='admin'

GEOSERVER_BASE_URL = SITEURL + "geoserver-geonode-dev/"
GEOSERVER_CREDENTIALS = "admin", "geoserver"

GEONETWORK_BASE_URL = SITEURL + "geonetwork/"
GEONETWORK_CREDENTIALS = "admin", 'admin'

GOOGLE_API_KEY = "replace.me.google.api"

REGISTRATION_OPEN = True

ACCOUNT_ACTIVATION_DAYS = 7

EMAIL_HOST = 'smtp.gmail.com'
EMAIL_HOST_USER = 'replace.me@gmail.com'
EMAIL_HOST_PASSWORD = 'replace.me.gmail.pw'
EMAIL_PORT = 587
EMAIL_USE_TLS = True

import logging
for _module in ["geonode.maps.views", "geonode.maps.gs_helpers"]:
    _logger = logging.getLogger(_module)
    _logger.addHandler(logging.StreamHandler())
    _logger.setLevel(logging.DEBUG)
