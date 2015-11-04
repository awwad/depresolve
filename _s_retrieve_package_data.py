import os       # for reading files
import sys      # for handling exceptions
import tarfile  # for exploring contents of .tar.gz source distributions
import tokenize # for parsing setup.py
import json     # to export dependency data

# <~> Retrieve package data from a local PyPI archive.
#     Ultimately, the goal is to fetch dependency information to be used in PyPI package
#       dependency resolver experiments.
#
#     This script assumes that dirTop (below) is set to the source directory of a
#       bandersnatch mirror of the PyPI archive.
#     
#     ASSUMPTIONS:
#        - sdists are .tar.gz files
#        - names of files do not contain '/' characters. :P
#        - metadata files are not binary files, but text files
#        - directory structure internal to .tar.gz files (the sdists) has substance to it
#            that is, setup.py is within a directory.
#            See comments in  find_metadata_files_in_package.
#        - no ill intent - this script employs tarfile.extract, which may be vulnerable to overwriting external files (e.g. if relative path is ../../../...) I'll prefer tarfile.extractfile, which I don't think would be vulnerable, but I'm not sure.
#


# <~> Constants, assumptions (module level)
BANDERSNATCH_MIRROR_DIR = '/srv/pypi/web/packages/source/'
SDIST_FILE_EXTENSION = '.tar.gz' # assume the archived packages bandersnatch grabs end in this
SETUPPY_FILETYPE = 'setup.py'
REQUIREMENTS_FILETYPE = "requirements.txt"
METADATA_FILETYPES = [SETUPPY_FILETYPE,REQUIREMENTS_FILETYPE] # These files, found in the sdists, will be inspected for package metadata. No string in this set should be a substring of any other string in this set, please.
DEBUG__N_SDISTS_TO_PROCESS = 50 # debug; max packages to explore during debug
#LOG__FAILURES = "_s_retrieve_package_data__failures.log"
JSON_OUTPUT_FILE_DEPENDENCIES = 'output/_s_out_dependencies.json' # the dependencies determined will be written here in JSON format.
JSON_OUTPUT_FILE_VERSIONS = 'output/_s_out_versions.json' # the list of detected packages will be written here in JSON format.
JSON_OUTPUT_FILE_ERRORS = 'output/_s_out_errors.json' # the list of errors will be written here

#     Error constants
ERROR_NO_SETUPPY = 1
ERROR_PARSING = 2 # should be broken out into individual error types, but the information is in the lower level function....


# <~> Rewriting main()
#     Crawl through the directory structure under BANDERSNATCH_MIRROR_DIR and pluck out sdists.
#     Given an sdist, find the setup.py file and process its requirements. 
def main():
  debug__n_sdists_processed = 0 # debug; counter for number of packages explored
  debug__n_metadata_files_found = 0 # debug; counter for number of metdata files found
  debug__n_failures_to_parse_metadata = 0
  dependencies_by_package = dict()
  parsed_versions_by_package = dict()
  failed_sdists = [] # list of sdists for which parsing failed, along with the failure type, in the form of 2-tuples ('tarfilename',ERROR_NUMBER)

  for dir,subdirs,files in os.walk(BANDERSNATCH_MIRROR_DIR):
    for fname in files:
      
      # If the file found isn't an sdist, move on to the next.
      if not is_sdist(fname):
        continue

      # Otherwise, we found an sdist. Load some temp variables to use.
      tarfilename_full = os.path.join(dir,fname)
      packagename = get_package_name_given_full_filename(tarfilename_full)
      packagename_withversion = get_package_and_version_string_from_full_filename(tarfilename_full)

      #print "Found presumed sdist: "+tarfilename_full+". Scanning it for interesting files."
      
      # I expect to move the following code into a helper function that will deal with packages one by one.

      # switching to a new func instead of find_setuppy_file_in_package
      #contained_metafilename = find_setuppy_file_in_package(tarfilename_full): # this func is a generator

      # Get all metadata files of interest in the sdist, in the form of a dict:
      #   e.g.:
      #     {'setup.py': 'foo/bar/setup.py',
      #      'restrictions.txt': 'foo/bar/baz/restrictions.txt'
      contained_metafilenames = find_metadata_files_in_package(tarfilename_full)

      # Skip this sdist if there was no setup.py file in it.
      if SETUPPY_FILETYPE not in contained_metafilenames:
        print "-SDist",tarfilename_full,"lacks a setup.py file. Skipping. Error type 1."
        debug__n_failures_to_parse_metadata += 1
        debug__n_sdists_processed += 1
        failed_sdists.append((tarfilename_full,ERROR_NO_SETUPPY))
        continue

      # Otherwise, we found a setup.py file and we continue.
      debug__n_metadata_files_found += 1
      
      # Note the setup.py filename, the package name, and the package name with version.
      contained_setuppy_filename = contained_metafilenames[SETUPPY_FILETYPE] # e.g. 'foo/bar/setup.py'
      
      # Initialize dependency strings list to fill it in the below try block.
      dependency_strings = []

      try:
        
        # Extract the metadata file into a file obj in memory,
        #   for parsing and copying purposes.
        contained_metafileobj = tarfile.open(tarfilename_full).extractfile(contained_setuppy_filename)
        
        # Make a local copy of the metadata file, writing to a file named using the
        #   tarfile name followed by the metadata filename.
        # TEMPORARILY COMMENTING OUT THE WRITE LINE
        #outfilename = fname+"."+contained_setuppy_filename[contained_setuppy_filename.rfind('/')+1:]
        #open(outfilename,'w').writelines(contained_metafileobj)
          
        # This function will parse the setup.py file (contained_metafileobj) and return dependency
        #   strings. In the event that it needs to read another of the sdist's files, e.g.
        #   restrictions.txt, it will pull that from the other two arguments.
        dependency_strings = find_dependencies_in_setuppy_fileobj(contained_metafileobj, tarfilename_full, contained_metafilenames)

        # Record information about the package for future storage.
        #   1. parsed_versions_by_package is a dictionary mapping a package name to the list of
        #        package versions discovered by the dependency finder, e.g.:
        #          {'potato': ['potato-1.0.0', 'potato-2.0.0'],
        #           'oracle': ['oracle-5.0'],
        #           'pasta':  ['pasta-1.0', 'pasta-2.0']}
        #
        #   2. dependencies_by_package is a dictionary mapping package versions to their
        #        discovered dependencies, e.g.:
        #           {'potato-1.0.0': ['tomato', 'pasta', 'oracle==5.0', 'foobar>=3.4'],
        #            'pasta-1.0': [],
        #            'pasta-2.0': [],
        #            'foobar-3.1': ['salsa']}
        #
        if packagename not in parsed_versions_by_package:
          parsed_versions_by_package[packagename] = []
        parsed_versions_by_package[packagename].append(packagename_withversion)
        dependencies_by_package[packagename_withversion] = dependency_strings

        # Report what was discovered, for debugging purposes.
        print "+SDist",tarfilename_full,"requires:",str(dependency_strings)

      # end of try
      except Exception, err:
        print "-SDist",tarfilename_full,"encountered exception. Skipping. Exception text:",str(err)
        failed_sdists.append((tarfilename_full, ERROR_PARSING))
        debug__n_failures_to_parse_metadata += 1
        
        
      debug__n_sdists_processed += 1

      # If we've finished the allotted number of sdists, report results and return.
      if debug__n_sdists_processed >= DEBUG__N_SDISTS_TO_PROCESS:
        report_results(debug__n_metadata_files_found, \
                         debug__n_sdists_processed, \
                         debug__n_failures_to_parse_metadata, \
                         dependencies_by_package, \
                         parsed_versions_by_package, \
                         failed_sdists)
        return
    # end of loop through files within a particular directory
  # end of loop over os.walk


def report_results(debug__n_metadata_files_found, \
                     debug__n_sdists_processed, \
                     debug__n_failures_to_parse_metadata, \
                     dependencies_by_package, \
                     parsed_versions_by_package, \
                     failed_sdists):
  
  print "Processing ending."
  print "  Found "+str(debug__n_metadata_files_found)+" metadata files in "+str(debug__n_sdists_processed)+" sdist archives."
  print "  Encountered",str(debug__n_failures_to_parse_metadata),"errors."
  with open(JSON_OUTPUT_FILE_VERSIONS,'w') as fobj_jsonoutput1:
    json.dump(parsed_versions_by_package,fobj_jsonoutput1)
  print "  Saved lists of packages versions discovered as a {package:[v1,v2,v3,...],package2:[v1...]} dict:",JSON_OUTPUT_FILE_VERSIONS
  with open(JSON_OUTPUT_FILE_DEPENDENCIES,'w') as fobj_jsonoutput2:
    json.dump(dependencies_by_package,fobj_jsonoutput2)
  print "  Saved lists of dependencies determined as a {package:[dep1,dep2,dep3,...],package2:[dep1...]} dict:",JSON_OUTPUT_FILE_DEPENDENCIES
  with open(JSON_OUTPUT_FILE_ERRORS,'w') as fobj_jsonoutput3:
    json.dump(failed_sdists,fobj_jsonoutput3)
  print "  Saved lists of failed dependency parses as a [(package1,error_id), (package2,error_id)] list:",JSON_OUTPUT_FILE_ERRORS

  # We should have one entry in failed_sdists per recorded failure.
  assert(debug__n_failures_to_parse_metadata == len(failed_sdists))
  # We should have one entry in failed_sdists or dependencies_by_package for each sdist processed.
  assert(len(failed_sdists) + len([sdist for sdist in dependencies_by_package]) == debug__n_sdists_processed)
  # We should see one entry in the version list for each sdist encountered.
  assert(debug__n_sdists_processed == sum([ len(parsed_versions_by_package[package]) for package in parsed_versions_by_package]))

  print "Assertions passed."


# <~> Given the fileobj for an sdist's setup.py file, find the dependencies in it,
#       based on a few simple models (see Daily Notes).
#
#     Breaks the model a bit and takes two additional arguments:
#       the full filename of the .tar.gz sdist file that contains the metafile we're dealing with.
#
#     This is so that if the setup.py file indicates that the dependencies are
#       in a requirements.txt file, we can pick that file out. It was either that
#       or return a magic number that could later be detected and replaced with
#       the results of reading the corresponding requirements.txt file.
#       I don't love it.
#
def find_dependencies_in_setuppy_fileobj(metafileobj, tarfilename_full, contained_metafilenames):

  #filecontents = metafileobj.read()
  #filecontents_by_line = metafileobj.readlines()
  
  dependency_strings = None # output
  in_docstring = False
  in_requires = False
  #in_setup_call = False # True when we are in the setup call parameter list

  # Employ the Python parsing tokenizer to scan forward in setup.py until
  #   we find a token that includes the string "requires"
  # Parse the full file into tokens and mark interesting tokens as we go.
  tokenizer = tokenize.generate_tokens(metafileobj.readline)

  tok_codes = []
  tok_values = []
  full_lines = []
  interesting_token_indices = []
  i = 0
  for tok_code,tok_value,(srow,scol),(erow,ecol),full_line in tokenizer:
    tok_codes.append(tok_code)
    tok_values.append(tok_value)
    full_lines.append(full_line)
    if  tok_value in ["requires","install_requires"] and tok_code == tokenize.NAME:
      interesting_token_indices.append(i)
    i += 1
    
  dependency_strings = []
  for i in interesting_token_indices: #Note that this can happen multiple times per setup.py, and also that the code below acts in ways as if it happens once.
      
    # If we see a NAME token (variable name in this case) that is
    #   either "requires" or "install_requires", then:
    if tok_values[i] in ["install_requires","requires"] and tok_codes[i] == tokenize.NAME:
      # Assume we're in the requirement specifying portion of the setup() call.
      # Should verify this here, but will handle that later.
      # (Otherwise, if the word requires appears in a name prior to the setup() call,
      #   it'll muck up this code.)


      # Now confirm that the pattern is matched.
      # The pattern we expect is roughly "requires = [ 'packagename'",
      if tok_values[i+1] == "=" and \
          tok_values[i+2] in ["[","("] and \
          tok_codes[i+3] == tokenize.STRING:
        # So we're at requires=[
        # We assume we found a simple single-line list of required packages
        #   specified by individual hard-coded strings.
        # For now, not dealing with multiple lines.
        j = i+2 # Set to just before the first string literal dependency (due to loop structure below starting with +1 statement)
        n_open_brackets = 0
        n_open_paren = 0
        if tok_values[i+2] == "[":
          n_open_brackets += 1
        else:
          assert(tok_values[i+2] == "(")
          n_open_paren += 1
        
          
        while n_open_brackets > 0 or n_open_paren > 0:
          assert(n_open_brackets >= 0 and n_open_paren >= 0) # Assert no bad or incomprehensible control structure.
          j += 1
          if tok_values[j] == ",":
            continue
          elif tok_values[j] == "[":
            n_open_brackets += 1
            continue
          elif tok_values[j] == "(":
            n_open_paren += 1
            continue
          elif tok_values[j] == "]":
            n_open_brackets -= 1
            continue
          elif tok_values[j] == ")":
            n_open_paren -= 1
            continue
          elif tok_codes[j] == tokenize.NL or tok_codes[j] == tokenize.COMMENT:
            raise Exception("This setup.py does not employ a simple, single-line, inline list of string literals in a requires= line. Reached newline or comment without brackets and parens being closed. Error type 2. The requires line reads:\n"+full_lines[i])
          elif tok_codes[j] == tokenize.STRING:
            dependency_strings.append(tok_values[j])
            continue
          else:
            raise Exception("Coding error or unexpected setup.py format- Unknown case reached while parsing requires line.")
          
      
      else: # if requires=[ pattern is not matched to begin with:
        if REQUIREMENTS_FILETYPE in full_lines[i]: # check for "requirements.txt" instead
          if REQUIREMENTS_FILETYPE not in contained_metafilenames:
            raise Exception("This setup.py includes a requires= line mentioning requirements.txt, but no requirements.txt file was found in the sdist. It will not be interpreted. Error type 3. The requires line reads:\n"+full_lines[i])
          else:
            dependency_strings = retrieve_dependencies_from_requirements_txt(tarfilename_full,contained_metafilenames)
        else:
          raise Exception("This setup.py neither employs a simple inline list of string literals in requires=, nor mentions requirements.txt. It will not be interpreted. The requires line reads:\n"+full_lines[i])
        
        
  if dependency_strings is None:
    raise Exception("No dependency information encountered.")
  else:
    return dependency_strings

    
# <~> Given an sdist .tar.gz filename and a dict of metafiles contained within it,
#       read the dependencies from the requirements file in the compressed sdist
#       and return those dependencies in a list of strings.
#
#     Raise an exception if no requirements.txt file is found.
#
def retrieve_dependencies_from_requirements_txt(tarfilename_full,contained_metafilenames):
  if REQUIREMENTS_FILETYPE not in contained_metafilenames:
    raise Exception("Requirements file not found.")
  else:
    with tarfile.open(tarfilename_full) as tarfileobj:
      return tarfileobj.extractfile(contained_metafilenames[REQUIREMENTS_FILETYPE]).read().splitlines()

#def process_single_line_dependencies(line):
#  pass




# <~> Rewritten as a non-generator function.
#    OLD COMMENTS:
#####     # <~> This is a generator function!
#####     Given an sdist file, yields info on each metadata file encountered.
#####     When a metadata file is encountered, yields:
#####        full internal filename of the metadata file in the tarfile
#
#     Looks for a setup.py file (matching SETUPPY_FILETYPE) in the given
#       sdist file object (a .tar.gz).
#     I assume that the contained metadata file is in some subdirectory.
#       It can't just be setup.py, for example, 
#       but must be e.g. abstract_rendering-0.0.2/setup.py
#
def find_setuppy_file_in_package(tarfilename_full):
  with tarfile.open(tarfilename_full) as tarfileobj:
    tarfile_contents_fnames = tarfileobj.getnames()
    for contained_fname in tarfile_contents_fnames:
      if contained_fname.endswith("/"+SETUPPY_FILETYPE):
        return contained_fname

# <~> Rewriting find_metadata_files_in_package as a non-generator, to return a dict.
#     Generally, I expect this to return a dict that looks like this:
# 
#         {'setup.py': 'somedirectory/setup.py',
#          'requirements.txt': 'somedirectory/requirements.txt'}
#
#     Strictly, the returned dictionary should contain:
#
#       One entry for each filetype in METADATA_FILETYPES that EXISTS
#         in the sdist provided, that entry being the first such file
#         encountered in the list of the sdist tarfile's contents.
#
#     Files are assumed to be metadata files if their filenames end with a
#       string in METADATA_FILETYPES
#
#     I assume that the contained metadata file is in some subdirectory.
#       It can't just be setup.py, for example, 
#       but must be e.g. abstract_rendering-0.0.2/setup.py
#
#     Behavior may be wonky if METADATA_FILETYPES contains strings that
#       are substrings of other strings in METADATA_FILETYPES.
#       (Possible skipped files, other crap.)
#
def find_metadata_files_in_package(tarfilename_full):
  with tarfile.open(tarfilename_full) as tarfileobj:
    tarfile_contents_fnames = tarfileobj.getnames()

  dict_of_contained_metadata_files = dict()

  # We only want the first instance of each type of file, so I'll pop items off this list as we go.
  remaining_metadata_filetypes = METADATA_FILETYPES

  for contained_fname in tarfile_contents_fnames:
    for i in range(0,len(remaining_metadata_filetypes)):
      filetype = remaining_metadata_filetypes[i]
      if contained_fname.endswith("/"+filetype): # Note that if a file matches multiple strings in METADATA_FILETYPES, that file will be reported multiple times. :P
        dict_of_contained_metadata_files[remaining_metadata_filetypes[i]] = contained_fname

  return dict_of_contained_metadata_files

  



# <~> Given a full filename of an sdist (of the form /srv/.../packagename/packagename-1.0.0.tar.gz),
#       return package name and version (e.g. packagename-1.0.0)
def get_package_and_version_string_from_full_filename(fname_full):
  #     get position of last / in full filename
  i_of_last_slash = fname_full.rfind('/')
  #     get position of .tar.gz in full filename
  i_of_targz = fname_full.rfind('.tar.gz')
  return fname_full[i_of_last_slash+1:i_of_targz]

# <~> Given a .tar.gz in a bandersnatch mirror, determine the package name.
#     Bing's code sees fit to assume that the parent directory name is the package name.
#     I'll go with that assumption.
def get_package_name_given_full_filename(fname_full):
  return get_parent_dir_name_from_full_path(fname_full)

# <~> Given a fully specified filename (i.e. including its path), extract name of parent directory (without full path).
def get_parent_dir_name_from_full_path(fname_full):
  #     get position of last / in full filename
  i_of_last_slash = fname_full.rfind('/')
  #     get position of 2nd to last / in full filename
  i_of_second_to_last_slash = fname_full[:i_of_last_slash].rfind('/')
  parent_dir = fname_full[i_of_second_to_last_slash+1:i_of_last_slash]

  return parent_dir

# <~> Returns true if the filename given is deemed that of an sdist file, false otherwise.
def is_sdist(fname):
  return fname.endswith(SDIST_FILE_EXTENSION)







if __name__ == "__main__":
  main()
