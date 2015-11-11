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
#        - run on a *NIX-based system ('/' dir slashes)
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
DEBUG__N_SDISTS_TO_PROCESS = 10000000 # debug; max packages to explore during debug
#LOG__FAILURES = "_s_retrieve_package_data__failures.log"
JSON_OUTPUT_FILE_DEPENDENCIES = 'output/_s_out_dependencies.json' # the dependencies determined will be written here in JSON format.
JSON_OUTPUT_FILE_VERSIONS = 'output/_s_out_versions.json' # the list of detected packages will be written here in JSON format.
JSON_OUTPUT_FILE_ERRORS = 'output/_s_out_errors.json' # the list of errors will be written here
EXTRACTED_SETUPPYS_DIR = 'extracted_setuppys/'

#     Error constants
ERROR_NO_SETUPPY = 1
ERROR_PARSING = 2 # should be broken out into individual error types, but the information is in the lower level function....


# <~> Rewriting main()
#     Crawl through the directory structure under BANDERSNATCH_MIRROR_DIR and pluck out sdists.
#     Given an sdist, find the setup.py file and process its requirements. 
def main():
  n_sdists_processed = 0 # debug; counter for number of packages explored
  n_metadata_files_found = 0 # debug; counter for number of metdata files found
  n_failures_to_parse_metadata = 0
  list_of_sdists_to_inspect = [] # Will be populated by all sdists in the BANDERSNATCH_MIRROR_DIR
  dependencies_by_package_version = dict()
  versions_by_package = dict()
  failed_sdists = [] # list of sdists for which parsing failed, along with the failure type, in the form of 2-tuples ('tarfilename',ERROR_NUMBER)


  # Argument processing. If we have arguments coming in, treat those as the sdists to inspect.
  # Otherwise, we'll scan everything in BANDERSNATCH_MIRROR_DIR
  if len(sys.argv) > 1:
    for arg in sys.argv[1:]:
      list_of_sdists_to_inspect.append(arg)
  else:
    i = 0
    for dir,subdirs,files in os.walk(BANDERSNATCH_MIRROR_DIR):
      for fname in files:
        if is_sdist(fname):
          list_of_sdists_to_inspect.append(os.path.join(dir,fname))
          i += 1
          if i >= DEBUG__N_SDISTS_TO_PROCESS: # awkward control structure, but saving debug run time
            break
      if i >= DEBUG__N_SDISTS_TO_PROCESS: # awkward control structure, but saving debug run time
        break


  for tarfilename_full in list_of_sdists_to_inspect:
    
    # Load some temp variables to use.
    packagename = get_package_name_given_full_filename(tarfilename_full)
    packagename_withversion = get_package_and_version_string_from_full_filename(tarfilename_full)
    
    # Record information about the package for future storage.
    #    versions_by_package is a dictionary mapping a package name to the list of
    #      package versions discovered by the dependency finder, e.g.:
    #          {'potato': ['potato-1.0.0', 'potato-2.0.0'],
    #           'oracle': ['oracle-5.0'],
    #           'pasta':  ['pasta-1.0', 'pasta-2.0']}
    #
    # If we don't have an entry for this package (e.g. potato) in the versions_by_package
    #   dict, create a blank one.
    if packagename not in versions_by_package:
      versions_by_package[packagename] = []
    # Then add this discovered version (e.g. potato-1.1) to the list for its package (e.g. potato)
    versions_by_package[packagename].append(packagename_withversion)
      
    
    # Get all metadata files of interest in the sdist, in the form of a dict:
    #   e.g.:
    #     {'setup.py': 'foo/bar/setup.py',
    #      'restrictions.txt': 'foo/bar/baz/restrictions.txt'
    contained_metafilenames = find_metadata_files_in_package(tarfilename_full)

    # Skip this sdist if there was no setup.py file in it.
    if SETUPPY_FILETYPE not in contained_metafilenames:
      print "-SDist",packagename_withversion,"lacks a setup.py file. Skipping. Error type 1."
      n_failures_to_parse_metadata += 1
      n_sdists_processed += 1
      failed_sdists.append((tarfilename_full,ERROR_NO_SETUPPY))
      continue

    # Otherwise, we found a setup.py file and we continue.
    n_metadata_files_found += 1
      
    # Choose the setup.py file from the list of metadata files found.
    contained_setuppy_filename = contained_metafilenames[SETUPPY_FILETYPE] # e.g. 'foo/bar/setup.py'
      
    # Initialize dependency strings list to fill it in the below try block.
    dependency_strings = []


    # Extract the metadata file into a file obj in memory,
    #   for parsing and copying purposes.
    try:
      contained_metafileobj = tarfile.open(tarfilename_full).extractfile(contained_setuppy_filename)
    except Exception, err:
      print "-SDist",packagename_withversion,": unable to expand setup.py file. Skipping. Error type 1.5. Exception text:",str(err)
      n_failures_to_parse_metadata += 1
      n_sdists_processed += 1
      failed_sdists.append((tarfilename_full,ERROR_NO_SETUPPY))
      continue

    # Make a local copy of the metadata file, writing to a file named using the
    #   tarfile name followed by the metadata filename.
    # Then, be sure to seek to the start of the file again so that we can still
    #   parse it afterwards.
    #outfilename = EXTRACTED_SETUPPYS_DIR + packagename_withversion + "." + contained_setuppy_filename[contained_setuppy_filename.rfind('/')+1:]
    #open(outfilename,'w').writelines(contained_metafileobj)
    #contained_metafileobj.seek(0,0)

    try:
      # This function will parse the setup.py file (contained_metafileobj) and return dependency
      #   strings. In the event that it needs to read another of the sdist's files, e.g.
      #   requirements.txt, it will pull that from the other two arguments.
      dependency_strings = find_dependencies_in_setuppy_fileobj(contained_metafileobj, tarfilename_full, contained_metafilenames)
    except Exception, err:
      print "-SDist",packagename_withversion,"encountered exception during find_dependencies_in_setuppy_fileobj. Skipping. Exception text:",str(err)
      failed_sdists.append((tarfilename_full, ERROR_PARSING))
      n_failures_to_parse_metadata += 1
      n_sdists_processed += 1
      continue
        
    # Record the dependency information garnered.
    #   dependencies_by_package_version is a dictionary mapping package versions to their
    #     discovered dependencies, e.g.:
    #           {'potato-1.0.0': ['tomato', 'pasta', 'oracle==5.0', 'foobar>=3.4'],
    #            'pasta-1.0': [],
    #            'pasta-2.0': [],
    #            'foobar-3.1': ['salsa']}
    #
    dependencies_by_package_version[packagename_withversion] = dependency_strings
    
    # Done processing this particular sdist. Report what was discovered for debugging purposes.
    n_sdists_processed += 1
    print "+SDist",packagename_withversion,"requires:",str(dependency_strings)



    # If we've finished the allotted number of sdists, stop looping.
    if n_sdists_processed >= DEBUG__N_SDISTS_TO_PROCESS:
      break
    # Else we're not done. Test assertions and continue.
    else:
      test_assertions(n_metadata_files_found, \
                        n_sdists_processed, \
                        n_failures_to_parse_metadata, \
                        dependencies_by_package_version, \
                        versions_by_package, \
                        failed_sdists)
      
  # end of loop through list_of_sdists_to_process

  # Report results (also testing assertions) and return.
  report_results(n_metadata_files_found, \
                   n_sdists_processed, \
                   n_failures_to_parse_metadata, \
                   dependencies_by_package_version, \
                   versions_by_package, \
                   failed_sdists)
  return


def report_results(n_metadata_files_found, \
                     n_sdists_processed, \
                     n_failures_to_parse_metadata, \
                     dependencies_by_package_version, \
                     versions_by_package, \
                     failed_sdists):
  
  print "Processing ending."
  print "  Found "+str(n_metadata_files_found)+" metadata files in "+str(n_sdists_processed)+" sdist archives."
  print "  Encountered",str(n_failures_to_parse_metadata),"errors."
  with open(JSON_OUTPUT_FILE_VERSIONS,'w') as fobj_jsonoutput1:
    json.dump(versions_by_package,fobj_jsonoutput1)
  print "  Saved lists of packages versions discovered as a {package:[v1,v2,v3,...],package2:[v1...]} dict:",JSON_OUTPUT_FILE_VERSIONS
  with open(JSON_OUTPUT_FILE_DEPENDENCIES,'w') as fobj_jsonoutput2:
    json.dump(dependencies_by_package_version,fobj_jsonoutput2)
  print "  Saved lists of dependencies determined as a {package:[dep1,dep2,dep3,...],package2:[dep1...]} dict:",JSON_OUTPUT_FILE_DEPENDENCIES
  with open(JSON_OUTPUT_FILE_ERRORS,'w') as fobj_jsonoutput3:
    json.dump(failed_sdists,fobj_jsonoutput3)
  print "  Saved lists of failed dependency parses as a [(package1,error_id), (package2,error_id)] list:",JSON_OUTPUT_FILE_ERRORS

  test_assertions(n_metadata_files_found, \
                    n_sdists_processed, \
                    n_failures_to_parse_metadata, \
                    dependencies_by_package_version, \
                    versions_by_package, \
                    failed_sdists)
  print "Assertions passed."


# <~> These assertions are tested after each sdist is processed, and after all
#       sdists have been processed.
def test_assertions(n_metadata_files_found, \
                      n_sdists_processed, \
                      n_failures_to_parse_metadata, \
                      dependencies_by_package_version, \
                      versions_by_package, \
                      failed_sdists):
  # We should have one entry in failed_sdists per recorded failure.
  assert(n_failures_to_parse_metadata == len(failed_sdists))
  # We should have one entry in failed_sdists or dependencies_by_package_version for each sdist processed.
  assert(len(failed_sdists) + len([sdist for sdist in dependencies_by_package_version]) == n_sdists_processed)
  # We should see one entry in the version list for each sdist encountered.
  assert(n_sdists_processed == sum([ len(versions_by_package[package]) for package in versions_by_package]))



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
  
  dependency_strings = [] # output
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
    
  # We'll go through multiple lines with possible dependency lists,
  #   so we'll use this bool to indicate when we've already found
  #   something worth parsing.
  have_found_dependencies = False

  for i in interesting_token_indices: #Note that this can happen multiple times per setup.py, and also that the code below acts in ways as if it happens once.

    # We're only interested in lines with:
    #    - token value equal to install_requires or requires
    #    - token code indicating the token is a name (token.NAME)
    # If that's not what we're looking at on this line, we can move on.
    if tok_values[i] not in ["install_requires","requires"] or tok_codes[i] != tokenize.NAME:
      continue

    # Otherwise, assume that we're dealing with a requirements specifying line.

    # If we see the pattern (roughly) "requires = [ 'packagename'",
    #   parse it.
    elif tok_values[i+1] == "=" and \
          tok_values[i+2] in ["[","("]:# and \
          #tok_codes[i+3] == tokenize.STRING:
      # So we're at requires=[
      # We assume we found a simple list of required packages
      #   specified by individual hard-coded strings.
      j = i+2 # Set to just before the first string literal dependency (due to loop structure below starting with +1 statement)
      n_open_brackets = 0
      n_open_paren = 0
      if tok_values[i+2] == "[":
        n_open_brackets += 1
      else:
        assert(tok_values[i+2] == "(")
        n_open_paren += 1
      
      # Loop over the tokens following requires=[ (or similar)
      #   until we're done processing this list.
      while n_open_brackets > 0 or n_open_paren > 0:
        assert(n_open_brackets >= 0 and n_open_paren >= 0) # Assert no bad or incomprehensible control structure.
        j += 1
        if tok_values[j] == "," or tok_codes[j] in [tokenize.NL,tokenize.COMMENT]:
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
        elif tok_codes[j] == tokenize.STRING:
          dependency = strip_outside_quotes(tok_values[j])
          dependency_strings.append(dependency)
          continue
        else:
          raise Exception("Coding error or unexpected setup.py format- Unknown case reached while parsing requires line. It is likely that the line does not match recognized patterns. Line reads:\n   "+full_lines[j])

      have_found_dependencies = True
      
    # Else, if requires=[ pattern is not matched to begin with,
    #   but we find a mention of a "requirements.txt" file, then
    #   try pulling dependency information out of "requirements.txt"
    elif REQUIREMENTS_FILETYPE in full_lines[i]: # check for "requirements.txt" instead
      if REQUIREMENTS_FILETYPE not in contained_metafilenames:
        raise Exception("This setup.py includes a requires= line mentioning requirements.txt, but no requirements.txt file was found in the sdist. It will not be interpreted. Error type 3. The requires line reads:\n"+full_lines[i])
      else:
        dependency_strings = retrieve_dependencies_from_requirements_txt(tarfilename_full,contained_metafilenames)
        have_found_dependencies = True

    # Else, if we see the following rough pattern: "requires = some_variable_name",
    #   then try re-parsing to figure out what's in THAT variable.
    # (This is the code that handles pre-filled lists of string literals.)
    elif tok_values[i+1] == "=" and \
          tok_codes[i+2] == tokenize.NAME and \
          tok_values[i+3] == ",": # eventually want to be more flexible with this pattern
      # This is where we re-parse the file and find the value of the variable being assigned to requires=.
      name_of_prefilled_variable = tok_values[i+2]

      metafileobj.seek(0,0)
      found = find_list_of_string_literals_with_name([name_of_prefilled_variable], metafileobj)
      # found is now None if there were no instances of the named variables
      #   that also fit a pattern.
      if found is None:
        continue
      else:
        dependency_strings = found
        have_found_dependencies = True

    # Else we haven't managed to encounter a comprehensible line.
    else:
      # To reach this point, we have to have to:
      #    - be dealing with a line with a "requires" or
      #        "install_requires" token with token type token.NAME.
      #    - be dealing with a line that does NOT match requires=[ (etc.)
      #    - not see mention of "requirements.txt" on this line
      #
      # In short, we have not found anything useful in this line.
      # Try the next interesting line.
      continue



  # end of looping through every interesting line (lines with "requires" or "install_requires" tokens)



  # Now we're done processing. Return information extracted or raise appropriate exceptions.

  # If we found dependency arguments to setup() and didn't have trouble parsing,
  # Or if there were no dependency arguments at all in the setup.py file,
  #    ( If we haven't found any instances of "requires" or "install_requires" tokens at all,
  #      then we can actually assume there are no official dependencies.)
  # Then we return the dependency information garnered (empty or otherwise).
  if have_found_dependencies or not interesting_token_indices:
    return dependency_strings


  # Last ditch effort, cheating a bit. If there's a requirements.txt file at all, go with its contents.
  elif REQUIREMENTS_FILETYPE in contained_metafilenames:
    print "((( Last ditch effort found requirements.txt file. )))"
    return retrieve_dependencies_from_requirements_txt(tarfilename_full,contained_metafilenames)

    

  else: # have not found dependencies, have no requirements.txt file, but saw "requires" or "install_requires" tokens.

    # Spool the requires lines to report them in the exception.
    interesting_lines = ""
    for k in interesting_token_indices:
      interesting_lines += full_lines[k]
      interesting_lines += "-------------------------------------------------------\n"
    raise Exception("Requirement tokens found, but were not able to be parsed. This setup.py neither employs a simple inline list of string literals in requires=, nor mentions requirements.txt in a line containing a requires token. It will not be interpreted. The various requires lines found read as follows:\n"+interesting_lines)
  
  

  assert(false) # control should never get here.


# <~> Given a list of variable names and an open file object for a python
#       source file, returns the value of the first variable with a matching
#       name found within that source file, if that variable's value is a
#       list of string literals in that source file.
#
#     For example, if given these arguments:
#       1- ["REQUIREMENTS","REQUIRED"]
#       2- read-only file object for a python file
#
#     where the python source reads, e.g.:
#
#       a = 5
#       c = 'potato'
#       d = ['soup','pasta','sandwich']
#       REQUIREMENTS = ['numpy', 'dancer==3.0']
#       setup(
#          ...,
#          install_requires=REQUIREMENTS,
#          ...
#       ...
#
#     then this function returns the list of strings ['numpy', 'dancer==3.0']
#
#
#     This function currently reproduces some existing functionality from
#       above in a slightly more general way, but with the difference that
#       it only seeks the first instance.
#     If everything works out, this should be made modular and consolidated.
#
def find_list_of_string_literals_with_name(names_of_desired_variables, fileobj):#, tok_values, tok_codes, full_lines):
  
  # Parse the contents of the python source file into three lists: tok_codes, tok_values, full_lines.
  tokenizer = tokenize.generate_tokens(fileobj.readline)
  tok_codes = []
  tok_values = []
  full_lines = []
  for tok_code,tok_value,(srow,scol),(erow,ecol),full_line in tokenizer:
    tok_codes.append(tok_code)
    tok_values.append(tok_value)
    full_lines.append(full_line)

  first_interesting_token = None
  values = [] # output

  # Consider this instead of the below:
  #   [i for i in range(0,len(tok_values)) if tok_values[i] in names_of_desired_variables]

  # Now loop over the tokens, in search of the first instance of an
  #   assignment to a variable name we're interested in.
  for i in range(0,len(tok_codes)):
    # We're only interested in tokens where:
    #    - token value equal to the name of a variable we're looking for
    #    - token code indicating the token is a name (token.NAME)
    #    - the next token is an "="
    # If that's not what we're looking at on this line, we can move on.
    if tok_values[i] not in names_of_desired_variables or \
          tok_codes[i] != tokenize.NAME or \
          tok_values[i+1] != '=' or \
          tok_values[i+2] not in ["[","("]:
      continue
    else:
      first_interesting_token = i
      break
  
  # If unable to find, return None.
  if first_interesting_token is None:
    # Last ditch effort in case of requirements.txt
#    for i in range(0,len(tok_codes)):
#      if tok_values[i] in names_of_desired_variables and \
#            tok_codes[i] == tokenize.NAME and \
#            REQUIREMENTS_FILETYPE in full_lines[i]:
#        retrieve_dependencies_from_requirements_txt()

    return None

  # Otherwise, assume that we're dealing with an interesting assignment line,
  #   matching the pattern (roughly):
  #     "interesting_variable_name = [ 'packagename'", ...
  #   so we parse it.
  i = first_interesting_token
  i += 2 # Set to just before the first string literal dependency (due to loop structure below starting with +1 statement)
  n_open_brackets = 0
  n_open_paren = 0
  if tok_values[i] == "[":
    n_open_brackets += 1
  else:
    assert(tok_values[i] == "(")
    n_open_paren += 1
      
  # Loop over the tokens following requires=[ (or similar)
  #   until we're done processing this list.
  while n_open_brackets > 0 or n_open_paren > 0:
    assert(n_open_brackets >= 0 and n_open_paren >= 0) # Assert no bad or incomprehensible control structure.
    i += 1
    if tok_values[i] == "," or tok_codes[i] in [tokenize.NL,tokenize.COMMENT]:
      continue
    elif tok_values[i] == "[":
      n_open_brackets += 1
      continue
    elif tok_values[i] == "(":
      n_open_paren += 1
      continue
    elif tok_values[i] == "]":
      n_open_brackets -= 1
      continue
    elif tok_values[i] == ")":
      n_open_paren -= 1
      continue
    elif tok_codes[i] == tokenize.STRING:
      thisvalue = strip_outside_quotes(tok_values[i])
      values.append(thisvalue)
      continue
    else:
      raise Exception("Coding error or unexpected python source file format- Unknown case reached while parsing assignment line.")


  return values


    
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




# <~> Given a string, assert that its outer characters are a matching set of quotation
#       marks (single or double, but matching) and strip them.
def strip_outside_quotes(s):
  assert s[0] in ['\'', '\"']
  assert s[-1:] == s[0]
  return s[1:-1]



if __name__ == "__main__":
  main()
