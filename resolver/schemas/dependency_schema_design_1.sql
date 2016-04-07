CREATE TABLE packagenames(
  pack_name TEXT PRIMARY KEY
)

CREATE TABLE dists(
  dist_key TEXT PRIMARY KEY,
  pack_name TEXT,
  vers_name TEXT,
  UNIQUE (pack_name, vers_name) ON CONFLICT REPLACE,
  FOREIGN KEY(pack_name) REFERENCES packagenames(pack_name)
)

CREATE TABLE dist_groups(
  group_id INT PRIMARY KEY,
  pack_name TEXT,
  FOREIGN KEY(pack_name) REFERENCES packagenames(pack_name)
)

CREATE TABLE dist_group_members(
  membership_id INT PRIMARY KEY,
  group_id INT,
  dist_key TEXT,
  UNIQUE (group_id, dist_id) ON CONFLICT REPLACE,
  FOREIGN KEY(dist_key) REFERENCES dists(dist_key),
  FOREIGN KEY(group_id) REFERENCES dist_groups(group_id)
)

CREATE TABLE dependencies(
  depender_dist_key TEXT,
  dependee_pack_name TEXT,
  dependee_group_id INT,
  PRIMARY KEY (depender_dist_key, dependee_pack_name),
  FOREIGN KEY(depender_dist_key) REFERENCES dists(dist_key),
  FOREIGN KEY(dependee_group_id) REFERENCES dist_groups(group_id)
)