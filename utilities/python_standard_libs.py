# Copyright 2010-2012 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""A list of top-level standard python library names.

This list is used by format-imports to determine if a module is in this group
or not.

The list is taken from http://docs.python.org/release/2.5.4/lib/modindex.html
but modules specific to other OSs have been taken out. It may need to be
updated from time to time.
"""


# Run this to generate a new module list.
if __name__ == '__main__':
    from lxml import html
    from operator import methodcaller
    from sys import version_info, stdout
    modindex_url = (
        "http://docs.python.org/release/"
        "{0}.{1}/modindex.html").format(*version_info)
    root = html.parse(modindex_url).getroot()
    modules = set(
        node.text.split(".", 1)[0]  # The "base" module name.
        for node in root.cssselect("table tt"))
    stdout.write("python_standard_libs = [\n")
    for module in sorted(modules, key=methodcaller("lower")):
        stdout.write("    %r,\n" % module)
    stdout.write("    ]\n")


python_standard_libs = [
    '__builtin__',
    '__future__',
    '__main__',
    '_winreg',
    'abc',
    'aepack',
    'aetools',
    'aetypes',
    'aifc',
    'al',
    'AL',
    'anydbm',
    'applesingle',
    'argparse',
    'array',
    'ast',
    'asynchat',
    'asyncore',
    'atexit',
    'audioop',
    'autoGIL',
    'base64',
    'BaseHTTPServer',
    'Bastion',
    'bdb',
    'binascii',
    'binhex',
    'bisect',
    'bsddb',
    'buildtools',
    'bz2',
    'calendar',
    'Carbon',
    'cd',
    'cfmfile',
    'cgi',
    'CGIHTTPServer',
    'cgitb',
    'chunk',
    'cmath',
    'cmd',
    'code',
    'codecs',
    'codeop',
    'collections',
    'ColorPicker',
    'colorsys',
    'commands',
    'compileall',
    'compiler',
    'ConfigParser',
    'contextlib',
    'Cookie',
    'cookielib',
    'copy',
    'copy_reg',
    'cPickle',
    'cProfile',
    'crypt',
    'cStringIO',
    'csv',
    'ctypes',
    'curses',
    'datetime',
    'dbhash',
    'dbm',
    'decimal',
    'DEVICE',
    'difflib',
    'dircache',
    'dis',
    'distutils',
    'dl',
    'doctest',
    'DocXMLRPCServer',
    'dumbdbm',
    'dummy_thread',
    'dummy_threading',
    'EasyDialogs',
    'email',
    'encodings',
    'errno',
    'exceptions',
    'fcntl',
    'filecmp',
    'fileinput',
    'findertools',
    'FL',
    'fl',
    'flp',
    'fm',
    'fnmatch',
    'formatter',
    'fpectl',
    'fpformat',
    'fractions',
    'FrameWork',
    'ftplib',
    'functools',
    'future_builtins',
    'gc',
    'gdbm',
    'gensuitemodule',
    'getopt',
    'getpass',
    'gettext',
    'gl',
    'GL',
    'glob',
    'grp',
    'gzip',
    'hashlib',
    'heapq',
    'hmac',
    'hotshot',
    'htmlentitydefs',
    'htmllib',
    'HTMLParser',
    'httplib',
    'ic',
    'icopen',
    'imageop',
    'imaplib',
    'imgfile',
    'imghdr',
    'imp',
    'importlib',
    'imputil',
    'inspect',
    'io',
    'itertools',
    'jpeg',
    'json',
    'keyword',
    'lib2to3',
    'linecache',
    'locale',
    'logging',
    'macerrors',
    'MacOS',
    'macostools',
    'macpath',
    'macresource',
    'mailbox',
    'mailcap',
    'marshal',
    'math',
    'md5',
    'mhlib',
    'mimetools',
    'mimetypes',
    'MimeWriter',
    'mimify',
    'MiniAEFrame',
    'mmap',
    'modulefinder',
    'msilib',
    'msvcrt',
    'multifile',
    'multiprocessing',
    'mutex',
    'Nav',
    'netrc',
    'new',
    'nis',
    'nntplib',
    'numbers',
    'operator',
    'optparse',
    'os',
    'ossaudiodev',
    'parser',
    'pdb',
    'pickle',
    'pickletools',
    'pipes',
    'PixMapWrapper',
    'pkgutil',
    'platform',
    'plistlib',
    'popen2',
    'poplib',
    'posix',
    'posixfile',
    'pprint',
    'profile',
    'pstats',
    'pty',
    'pwd',
    'py_compile',
    'pyclbr',
    'pydoc',
    'Queue',
    'quopri',
    'random',
    're',
    'readline',
    'repr',
    'resource',
    'rexec',
    'rfc822',
    'rlcompleter',
    'robotparser',
    'runpy',
    'sched',
    'ScrolledText',
    'select',
    'sets',
    'sgmllib',
    'sha',
    'shelve',
    'shlex',
    'shutil',
    'signal',
    'SimpleHTTPServer',
    'SimpleXMLRPCServer',
    'site',
    'smtpd',
    'smtplib',
    'sndhdr',
    'socket',
    'SocketServer',
    'spwd',
    'sqlite3',
    'ssl',
    'stat',
    'statvfs',
    'string',
    'StringIO',
    'stringprep',
    'struct',
    'subprocess',
    'sunau',
    'sunaudiodev',
    'SUNAUDIODEV',
    'symbol',
    'symtable',
    'sys',
    'sysconfig',
    'syslog',
    'tabnanny',
    'tarfile',
    'telnetlib',
    'tempfile',
    'termios',
    'test',
    'textwrap',
    'thread',
    'threading',
    'time',
    'timeit',
    'Tix',
    'Tkinter',
    'token',
    'tokenize',
    'trace',
    'traceback',
    'ttk',
    'tty',
    'turtle',
    'types',
    'unicodedata',
    'unittest',
    'urllib',
    'urllib2',
    'urlparse',
    'user',
    'UserDict',
    'UserList',
    'UserString',
    'uu',
    'uuid',
    'videoreader',
    'W',
    'warnings',
    'wave',
    'weakref',
    'webbrowser',
    'whichdb',
    'winsound',
    'wsgiref',
    'xdrlib',
    'xml',
    'xmlrpclib',
    'zipfile',
    'zipimport',
    'zlib',
    ]
