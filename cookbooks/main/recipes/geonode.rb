release = "GeoNode-1.0.tar.gz"

remote_file "/tmp/#{release}" do
     source "http://dev.geonode.org/release/#{release}"
      mode "0644"
end
