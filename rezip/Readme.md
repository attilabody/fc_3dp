# FreeCad document handing with git example

FreeCad stores its douments compressed in zip file format. This makes git's delta compression actually unusable as all the document revisions will be totally different. Unfortunately the freecad documant loader implemantation heavily depends on the availability of some "files" being available at the beginning of the archive, so simply unzipping the document and rezipping with 0 compression level will not work.

The supplied rezip.zh script unzips a zip archive into the temp folder and rezips it retaining the order of the files in the original archive, using an user specified compression level (0 by default).

This repository serves as an example for setting up a git repo to recompress the .FCStd files during commit with 0 compression level, gicing a chance to go git to store the changes more efficiently.

## Usage
- Copy the __*rezip.sh*__ script to any folder which is included in the search path.
- Make sure that zip and unzip commands are available on your system.
- Append the content of the file __*config*__ to your repository's __*.git/config*__ file.
- Copy __*.gitattributes*__ to the root of your repository.