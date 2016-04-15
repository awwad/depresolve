CREATE TABLE dependency_relationships(
  dependency_id INT PRIMARY KEY,
  depender_dist_key TEXT,
  dependee_package_name TEXT,
  compatible_versions TEXT,
  UNIQUE(depender_dist_key, dependee_package_name) ON CONFLICT REPLACE
)

CREATE TABLE satisfying_dists(
  dependency_id INT,
  compatible_dist_key TEXT,
  PRIMARY KEY(dependency_id, compatible_dist),
  FOREIGN KEY(dependency_id) REFERENCES dependency_relationships(dependency_id) 
)