#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Extract the list of included figures from a latex source file"""


from sys import stderr, stdin
import re
import os.path as op
import argparse as ap
from glob import glob


# Order reflects priority
ALLOWED_EXT = ['.pdf', '.png', '.jpg', '.jpeg', '.gif', '.eps']
ALLOWED_EXT += [_.upper() for _ in ALLOWED_EXT]

COMMENT_REGEX = re.compile(r'%.*(?=\r?\n|$)$', re.MULTILINE)

# For positive control: count each occurence of the command.
# Do not capture match.
COMMAND_REGEX = re.compile(r'(?=\\(includegraphics|multiinclude|uncovergraphics)\b)')

GR_PAT = r'''#^[^%\n]*             # Uncommented line
\\(includegraphics|multiinclude|uncovergraphics)
\s*
(<.*>\s*)?                           # Overlay specification
(\[(?:.|\n)*?\]\s*)?                # Options
\{\s*(.+?)                          # path to file
(\}\.[a-zA-Z0-9]+)?          # If extra pair of brackets
\s*\}.*[{\\n]?
'''
#GR_PAT = r'^[^%]*?\\(includegraphics|multiinclude)(<.*>)?\s*(\[.*?\]\s*)?\{\s*([^\n]*)\s*\}(\.[a-zA-Z0-9]\s*\})?'
GR_REGEX = re.compile(GR_PAT, (re.MULTILINE | re.VERBOSE))


def get_fig_list(infile):

    with (stdin if infile=='-' else open(infile)) as f:
        source = f.read()

    all_cmds = len(COMMAND_REGEX.findall(source)) # better than str.count?
    # Delete comments
    source = COMMENT_REGEX.sub('', source)
    uncom_cmds = len(COMMAND_REGEX.findall(source))
    # Positive control
    print("    [%s]:Found %d include commands (%d uncommented)." % (
            infile, all_cmds, uncom_cmds),
          file=stderr)

    matched = []
    command = []
    options = []
    path = []
    ext = []

    for match in GR_REGEX.finditer(source):
        matched.append(match.group(0))
        command.append(match.group(1))
        options.append(match.group(3))
        path.append(match.group(4))
        ext_str = match.group(5)
        if ext_str:
            ext_str = ext_str.lstrip('}')
            path[-1] += '}'
        ext.append(ext_str)
        #print(path[-1], ext[-1])
        #if command[-1] == 'multiinclude': print(match.groups())
    #print(match.groups())

    assert len(matched) == uncom_cmds
    return matched, command, options, path, ext


def get_abspath(fn, sourcedir='.'):
    """Expand ~, ~username, $HOME or get absolute path."""
    fn = op.expanduser(fn)
    if not op.isabs(fn):
        fn = op.abspath(op.join(sourcedir, fn))
    return fn


def get_implicit_ext_files(abspathroot, uniq=False, allowed_ext=ALLOWED_EXT):
    files = []
    for e in allowed_ext:
        if op.isfile(abspathroot + e) or op.islink(abspathroot + e):
            files.append(abspathroot + e)
            if uniq: break

    return files


def parse_ext_includegraphics(p, relp, absp, e=None, allowed_ext=ALLOWED_EXT):
    filename = absp
    if e:
        filename += e
    elif not p.endswith('}'):
        _, e = op.splitext(relp)
        if e and e not in allowed_ext:
            raise ValueError('Invalid includegraphics extension %r (%s)' % (e, p))
    return filename, e


def figs2files(sourcefile, matched, command, options, path, ext, raise_=False,
               src_dir=None, uniq=False):
    """Find the filenames each include corresponds to."""
    # capture \multiinclude option values

    ext_re   = re.compile(r'format\s*=\s*([a-zA-Z-0-9]+)\s*[,\]]')
    start_re = re.compile(r'start\s*=\s*([0-9]+)\s*[,\]]')
    end_re   = re.compile(r'end\s*=\s*([0-9]+)\s*[,\]]')

    sourcedir = op.dirname(sourcefile) if src_dir is None else src_dir

    actual_files = []

    for i, (m,cmd,opt,p,e) in enumerate(
                                zip(matched,command,options,path,ext)):
        relp = p.replace('\\string', '').lstrip('{\t ').rstrip('}\t ')
        absp = get_abspath(relp, sourcedir)
        #print(absp)

        if cmd == 'multiinclude':
            # Search filename using the start of the absolute path
            fn_pattern = absp.replace('%', '%%')

            # Get start from options
            start_m = start_re.search(opt)
            start = int(start_m.group(1)) if start_m else 0

            # get ext
            ext_m = ext_re.search(opt)
            if ext_m:
                e = '.' + ext_m.group(1)
                fn_pattern += '-%s' + e
            else:
                fn_pattern += '.%s'
                # That's what multiinclude does (MetaPost output).

            # get end
            end_m = end_re.search(opt)
            if end_m:
                end = int(end_m.group(1))
                filenames = [fn_pattern % number for number in range(start, end+1)]
            else:
                end = None
                filenames = set()  # /!\ different type
                
                # Escape any '%' to avoid unexpected string formatting error
                # Escape but keep formatting signs ok.
                re_fn_nb = re.compile(
                                re.escape(fn_pattern).replace(r'\%', '%') % \
                                    r'(\d+)')
                
                for fn in glob(fn_pattern % '*'):
                    number_match = re_fn_nb.search(fn)
                    if number_match and int(number_match.group(1))>=start:
                        filenames.add(fn)

            #print('ext:', e, 'start:', start, 'end:', end,
            #      'N:', len(filenames))
                
        elif cmd == 'includegraphics' or cmd == 'uncovergraphics':
            filename, e = parse_ext_includegraphics(p, relp, absp, e)
            filenames = [filename]
        
        if not filenames:
            msg = 'No files for %r' % p
            if _raise:
                raise FileNotFoundError(msg)
            else:
                print('WARNING:' + msg, file=stderr)

        if not e:
            for fn in filenames:
                foundfiles = get_implicit_ext_files(fn, uniq)
                if not foundfiles:
                    msg = 'No files for %r' % fn
                    if raise_:
                        raise FileNotFoundError(msg)
                    else:
                        print('WARNING:' + msg, file=stderr)

                actual_files.extend(foundfiles)
        else:
            for fn in filenames:
                if not op.isfile(fn) and not op.islink(fn):
                    msg = "Not a file/link: %r" % fn
                    if raise_:
                        raise FileNotFoundError(msg)
                    else:
                        print('WARNING:' + msg, file=stderr)
            actual_files.extend(filenames)

    return sorted(set(actual_files))


def main(infiles, raise_=False, file_check=True, src_dir=None, uniq=False):
    for infile in infiles:
        figs = get_fig_list(infile)
        #print(len(figs[0]), '\n---')

        if len(figs[0]):
            if not file_check:
                for p,e in zip(*figs[-2:]):
                    relp = p.replace('\\string', '').lstrip('{\t ').rstrip('}\t ')
                    print(relp)
            else:
                figfiles = figs2files(infile, *figs, raise_=raise_,
                                      src_dir=src_dir, uniq=uniq)
                print("    [%s]:Found %d files for %d include commands." \
                        % (infile, len(figfiles), len(figs[0])),
                      file=stderr)
                if figfiles:
                    print('\n'.join(figfiles))
            #print([len(s) for s in figs])


if __name__ == '__main__':
    parser = ap.ArgumentParser(description=__doc__)
    parser.add_argument('infiles', nargs='+', help="'-' for stdin.")
    parser.add_argument('-r', '--raise', dest='raise_', action='store_true',
                        help='Raise FileNotFoundError instead of simple warning.')
    parser.add_argument('-n', '--no-check', '--no-file-check',
                        dest='file_check', action='store_false',
                        help='Do not glob files and do not check if they exist.')
    parser.add_argument('-s', '--src-dir', '--source-dir',
                        help='Directory from where pdflatex is run.')
    parser.add_argument('-u', '--uniq', action='store_true',
                        help=('If multiple matching files (different extensio'
                              'ns, only output one (by priority, i.e. pdf fir'
                              'st)'))

    args = parser.parse_args()
    main(**vars(args))

