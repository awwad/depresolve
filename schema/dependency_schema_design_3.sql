CREATE TABLE IF NOT EXISTS elaborated_dependencies(
  depender_dist_key TEXT,
  satisfying_pack_name TEXT,
  satisfying_dist_key TEXT,
  PRIMARY KEY(depender_dist_key, satisfying_dist_key) ON CONFLICT REPLACE
)

CREATE TABLE IF NOT EXISTS dependency_specifiers(
  depender_dist_key TEXT,
  satisfying_pack_name TEXT,
  satisfying_specifier TEXT,
  PRIMARY KEY(depender_dist_key, satisfying_pack_name) ON CONFLICT REPLACE
)

CREATE TABLE IF NOT EXISTS dists_with_no_dependencies(
  depender_dist_key TEXT,
  PRIMARY KEY(depender_dist_key) ON CONFLICT REPLACE
)

CREATE TABLE IF NOT EXISTS packages_without_version_info(
  pack_name TEXT,
  PRIMARY KEY(pack_name) ON CONFLICT REPLACE
)

CREATE TABLE IF NOT EXISTS missing_dependencies(
  depender_dist_key TEXT,
  satisfying_pack_name TEXT,
  PRIMARY KEY(depender_dist_key, satisfying_pack_name) ON CONFLICT REPLACE
)


# Could also incorporate this, and foreign key it from those above.
# Not worth it right now.... maybe later?

#CREATE TABLE IF NOT EXISTS dists(
#  distkey TEXT,
#  PRIMARY KEY(distkey) ON CONFLICT REPLACE
#)
