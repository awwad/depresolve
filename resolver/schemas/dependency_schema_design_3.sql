CREATE TABLE IF NOT EXISTS dependencies(
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

CREATE TABLE IF NOT EXISTS packages_without_available_version_info(
  pack_name TEXT,
  PRIMARY KEY(pack_name) ON CONFLICT REPLACE
)

CREATE TABLE IF NOT EXISTS dists_with_missing_dependencies(
  depender_dist_key TEXT,
  satisfying_pack_name TEXT,
  PRIMARY KEY(depender_dist_key, satisfying_pack_name) ON CONFLICT REPLACE
)

CREATE TABLE IF NOT EXISTS dists(
  distkey TEXT,
  PRIMARY KEY(distkey) ON CONFLICT REPLACE
)
