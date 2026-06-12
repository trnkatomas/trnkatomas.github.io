# the very first step was to mine the data from the size by some xhtml magic, or by some other means in the browser, the site is no longer operational, which is the reason I decided to make this public but it also means that I'm unable to replicate the inital data gathering step

# attempt to pinpoint the location - but it turned out to be just the zone to which the car belongs
# curl 'http://ags.cuzk.cz/arcgis/rest/services/RUIAN/Vyhledavaci_sluzba_nad_daty_RUIAN/MapServer/exts/GeocodeSOE/findAddressCandidates?SingleLine=Praha+Dejvicka&magicKey=&outSR=4326&maxLocations=&outFields=&searchExtent=&f=pjson'


find ./ -name "*.json" | parallel "cat {} | jq -r '.results | .[] | [.id, .created, .reservation_start, .reservation_end, .user.id, .vehicle.id, .vehicle.brand, .vehicle.model, .vehicle.address1, .vehicle.city, .vehicle.zip] | @tsv' > {.}.tsv"

cat *.tsv > last_year.tsv
