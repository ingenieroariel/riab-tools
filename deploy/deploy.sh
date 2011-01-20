#!/bin/sh

## deploy.sh - automatically unpack a geonode release and deploy the various
## server components to the appropriate locations

if [ -z "$1" ]
then 
    echo "Please provide the name of the GeoNode bundle to deploy."
    exit
fi

# first argument must be the path to the GeoNode release package
RELEASE_PACKAGE="$1"

# Copy the following to ./deploy.local.sh to set up server's local deployment configuration.
# TOMCAT_USER=tomcat6
# TOMCAT_HOME=/opt/apache-tomcat-6.0.24/
# GEOSERVER_DATA_DIR=/var/lib/geoserver_data/geonode/
# HTTPD_USER=www-data
# DJANGO_DEPLOY_DIR=/var/www/wsgi/geonode/
# MEDIA_BASE=http://localhost/media/
# GOOGLE_API_KEY=""
# GEONODE_BASE_URL=http://demo.geonode.org/
# GEOSERVER_BASE_URL=http://localhost/geoserver-geonode-dev/
# GEOSERVER_CREDENTIALS='"admin", "geoserver"' # python tuple literal, gets pasted into code (eeew)
# GEONETWORK_BASE_URL=http://localhost/geonetwork/
# GEONODE_UPLOAD_PATH = /var/www/htdocs/static/
# MEDIA_DIR=/var/www/html/media/
# MEDIA_URL=$GEOSERVER_BASE_URL/www
# MEDIA_ROOT=/var/www/geonode/media/
# SITEURL=http://localhost/


if [ -r "deploy.local.sh" ] 
then 
    . ./deploy.local.sh
else
    echo "Please create a local install profile. (See this script's source for details.)"
    exit
fi

# Some internal details that it still makes sense to extract out as variables
GEOSERVER_WAR=geoserver-geonode-dev.war
GEONETWORK_WAR=geonetwork.war
WORKDIR=/tmp/geonode-work/

function unpack_release () {
  echo "Unpacking release bundle..."
  rm -rf $WORKDIR
  mkdir $WORKDIR
  gunzip -c $RELEASE_PACKAGE | (cd $WORKDIR && tar xf -)
  WORKDIR=$WORKDIR`basename $RELEASE_PACKAGE .tar.gz`/

}

function update_webinf () {
  WEB_XML=WEB-INF/web.xml
  pushd $WORKDIR
  unzip -qq $GEOSERVER_WAR $WEB_XML
  INSERT_AT=$(
    # grep -n gets the line prefixed with a line number
    grep -n GEOSERVER_DATA_DIR $WEB_XML | 
    # use sed to extract just the line number
    sed 's!\([0-9]\+\):.*!\1!'
  )
  INSERT_AT=$(expr 4 + $INSERT_AT)
  (
    head -n $INSERT_AT $WEB_XML
    cat << EOF
    <context-param>
    <param-name>GEOSERVER_DATA_DIR</param-name>
    <param-value>${GEOSERVER_DATA_DIR}</param-value>
    </context-param>

    <context-param>
    <param-name>GEONODE_BASE_URL</param-name>
    <param-value>${GEONODE_BASE_URL}</param-value>
    </context-param>
EOF
    tail -n +$(expr 1 + $INSERT_AT) $WEB_XML
  )> ${WEB_XML}.new
  mv ${WEB_XML}.new ${WEB_XML}
  zip -qq $GEOSERVER_WAR $WEB_XML
  rm -rf $(dirname $WEB_XML)
  popd
}

function deploy_webapp () {
  WARFILE="$1"
  rm -rf "${TOMCAT_HOME}/webapps/$(basename $WARFILE .war)"
  rm "${TOMCAT_HOME}/webapps/$(basename $WARFILE)"
  chown $TOMCAT_USER "${WORKDIR}/${WARFILE}"
  mv "${WORKDIR}/${WARFILE}" "${TOMCAT_HOME}/webapps/"
}

function deploy_tomcat_webapps () {
  echo "Deploying GeoServer..."
  ## deploying geoserver consists of:
  ## * rewrite WEB-INF/web.xml to point to the proper GeoServer datadir
  update_webinf # see function above for details
  
  ## * bring Tomcat down (gently if possible)
  echo "Switching users to $TOMCAT_USER"
  /etc/init.d/tomcat6 stop
  sleep 10 # seconds
  killall -9 java
  
  ## * move geoserver WAR into Tomcat
  deploy_webapp "$GEOSERVER_WAR"
  deploy_webapp "$GEONETWORK_WAR"
  
  ## * bring Tomcat back up
  echo "Switching users to $TOMCAT_USER"
  /etc/init.d/tomcat6 start
}

function deploy_django_app () {
  echo "Deploying Django App..."
  ## deploying the django app consists of:

  ## * replace previous django app with the new one
  DJANGO_BACKUP="$(dirname "$DJANGO_DEPLOY_DIR")/$(basename "$DJANGO_DEPLOY_DIR").bk"
  rm -rf "$DJANGO_BACKUP"
  mv "$DJANGO_DEPLOY_DIR" "$DJANGO_BACKUP"
  mv "$WORKDIR" "$DJANGO_DEPLOY_DIR"

  ## * execute bootstrap script
  (cd "$DJANGO_DEPLOY_DIR" && python bootstrap.py)

  ## copy in local settings
  cp local_settings.py "$DJANGO_DEPLOY_DIR/src/GeoNodePy/geonode/"

  ## * transfer database (ie, copy over the sqlite file)
  if [ -e "$DJANGO_BACKUP/production.db" ] 
  then
    cp "$DJANGO_BACKUP/production.db" "$DJANGO_DEPLOY_DIR"
  fi

  pushd "$DJANGO_DEPLOY_DIR" 
  . bin/activate
  django-admin.py syncdb --settings=geonode.settings --noinput  
  popd
  
  chown $HTTPD_USER -R "$DJANGO_DEPLOY_DIR"
}

function deploy_media () {
  echo "Deploying Client Media..."
  ## deploying the media consists of:
  ## * wipe previous generation of media
  rm "$MEDIA_DIR" -rf

  ## * unpack new media to appropriate location
  unzip -qq "$WORKDIR/geonode-client.zip" -d "$MEDIA_DIR"

  chown $HTTPD_USER -R "$MEDIA_DIR"
}

unpack_release
deploy_tomcat_webapps
deploy_media
deploy_django_app 

/etc/init.d/apache2 restart
