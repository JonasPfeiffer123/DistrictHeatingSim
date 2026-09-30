# Bundled map libraries

`map.html` loads these from here instead of a CDN, so the map and the network editor work
without internet access (only the base-map tiles are fetched online). Files are unmodified
copies of the published releases; each folder carries the library's license.

| Folder | Library | Source | License |
|---|---|---|---|
| `leaflet-1.9.4/` | Leaflet 1.9.4 (`leaflet.css`, `leaflet.js`, `images/`) | `https://unpkg.com/leaflet@1.9.4/dist/` | BSD-2-Clause |
| `proj4-2.12.1/` | proj4js 2.12.1 (`proj4.js`) | `https://cdnjs.cloudflare.com/ajax/libs/proj4js/2.12.1/` | MIT |
| `leaflet-geoman-free-2.20.2/` | Leaflet-Geoman free 2.20.2 (`leaflet-geoman.css`, `leaflet-geoman.min.js`) | `https://unpkg.com/@geoman-io/leaflet-geoman-free@2.20.2/dist/` | MIT |

Integrity (identical to the SRI hashes the CDN version was pinned with):

| File | Hash |
|---|---|
| `leaflet.css` | `sha256-p4NxAoJBhIIN+hmNHrzRCf9tD/miZyoHS5obTRR9BMY=` |
| `leaflet.js` | `sha256-20nQCchB9co0qIjJZRGuk2/Z9VM+kNiyxNV1lvTlZBo=` |
| `leaflet-geoman.css` | `sha384-++juJE6hRzkkV4Ri9H2C+3yjCTdEk4PaZxptm3cpgKKjuMcAHErn35Q/0sGitZCR` |
| `leaflet-geoman.min.js` | `sha384-pXNWPiDuE2DMvhW70luPUxtqU3gGa3Fn+Q4CckIXyA9ZcnByNj6FgpHi8Km45rcc` |

To update a library: download the new release files from the same source into a new
versioned folder (plus its license), point `map.html` at it, delete the old folder, update
this file, and check the map + network editor by hand in the app (there is no automated test
for the embedded web view).
