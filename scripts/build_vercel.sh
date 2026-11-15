#!/usr/bin/env sh
# Build the Vercel bundle: static dashboard goes to public/ (served by the CDN),
# the API runs as a Python function from app.py. MapLibre loads from unpkg with
# Subresource Integrity in the hosted build.
set -eu
rm -rf public && mkdir public
cp web/styles.css web/app.js web/privacy.html web/favicon.svg public/
JS=$(openssl dgst -sha384 -binary web/vendor/maplibre-gl.js | openssl base64 -A)
CSS=$(openssl dgst -sha384 -binary web/vendor/maplibre-gl.css | openssl base64 -A)
sed "s#href=\"vendor/maplibre-gl.css\"#href=\"https://unpkg.com/maplibre-gl@4.7.1/dist/maplibre-gl.css\" integrity=\"sha384-$CSS\" crossorigin=\"anonymous\"#; s#src=\"vendor/maplibre-gl.js\"#src=\"https://unpkg.com/maplibre-gl@4.7.1/dist/maplibre-gl.js\" integrity=\"sha384-$JS\" crossorigin=\"anonymous\"#" web/index.html > public/index.html
echo "public/ ready. Set TRUST_PROXY=1 in the Vercel project, then deploy."
