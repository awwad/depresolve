"""
<Program Name>
  scrape_pypi_metadata.py

<Purpose>
  Script to scrape all distribution metadata from PyPI via the xmlrpc
  interface. Stores data in files: OUTPUT_FNAME_METADATA,
  OUTPUT_FNAME_VERSIONS, OUTPUT_FNAME_DISTKEYS.
  If interrupted, stores data in filenames postpended with '_aborted'.
  Recovers on next run if interrupted (except that you should move the
  _aborted files to the proper filename).

  Note that the static metadata in PyPI is generally lacking in terms of
  dependencies.


"""
import depresolve
import depresolve.depdata as data # for distkey_format and load_json_db
import json

OUTPUT_FNAME_METADATA = 'data/metadata_by_distkey.json'
OUTPUT_FNAME_VERSIONS = 'data/versions_by_package.json'
OUTPUT_FNAME_DISTKEYS = 'data/distkey_to_packver.json'

def write_file(to_dump, fname):
  json.dump(to_dump, open(fname, 'w'))

metadata_by_distkey = data.load_json_db(OUTPUT_FNAME_METADATA)
versions_by_package = data.load_json_db(OUTPUT_FNAME_VERSIONS)
# Just in case of casing issues and such:
distkey_to_packver_map = data.load_json_db(OUTPUT_FNAME_DISTKEYS) 

try:
  import xmlrpclib
except ImportError:
  import xmlrpc.client as xmlrpclib
client = xmlrpclib.ServerProxy('https://pypi.python.org/pypi')
packages = client.list_packages()

n_packs_processed = 0
n_total_packages = len(packages)

try: #Making this retry-friendly.
  for p in packages:
    n_packs_processed += 1
    print('Processing package ' + p + '(' + str(n_packs_processed) + '/' +
        str(n_total_packages) + ')')
    # If we lack the catalog of versions for this package, get it from PyPI.
    if p not in versions_by_package:
      versions_by_package[p] = client.package_releases(p, True)

    for v in versions_by_package[p]:
      distkey = data.distkey_format(p, v)
      distkey_to_packver_map[distkey] = (p, v)

    # If we lack the metadata for this version, fetch it.
    if distkey not in metadata_by_distkey:
      metadata_by_distkey[distkey] = client.release_data(p, v)

    print('Done with package  ' + p)

except:
  print('----- Process interrupted by exception. Dumping data before '
      're-raising. Data filenames prepended with "aborted_".')
  write_file(metadata_by_distkey, OUTPUT_FNAME_METADATA + '_aborted')
  write_file(versions_by_package, OUTPUT_FNAME_VERSIONS + '_aborted')
  write_file(distkey_to_packver_map, OUTPUT_FNAME_DISTKEYS + '_aborted')
  print('Data dumped.')
  raise

write_file(metadata_by_distkey, OUTPUT_FNAME_METADATA)
write_file(versions_by_package, OUTPUT_FNAME_VERSIONS)
write_file(distkey_to_packver_map, OUTPUT_FNAME_DISTKEYS)









