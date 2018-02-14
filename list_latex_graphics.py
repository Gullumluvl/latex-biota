#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Extract the list of included figures from a latex source file"""


from sys import stderr
import re
import os.path as op
import argparse as ap
from glob import glob


ALLOWED_EXT = ['.png', '.jpg', '.pdf', '.gif', '.eps']
ALLOWED_EXT += [_.upper() for _ in ALLOWED_EXT]


def get_fig_list(infile):
    
    # TODO: check that line is not commented out

    comment_regex = re.compile(r'%.*$')

    #fig_regex = re.compile(r'\\includegraphics',
    #fig_regex = re.compile(r'\\includegraphics\s*(\[.*?\])?',
    gr_pat = r'''#^[^%\n]*             # Uncommented line
    \\(includegraphics|multiinclude)
    \s*
    (<.*>\s*)?                           # Overlay specification
    (\[(?:.|\n)*?\]\s*)?                # Options
    \{\s*(.+?)                          # path to file
    (\}\.[a-zA-Z0-9]+)?          # If extra pair of brackets
    \s*\}.*[{\\n]?
    '''
    #gr_pat = r'^[^%]*?\\(includegraphics|multiinclude)(<.*>)?\s*(\[.*?\]\s*)?\{\s*([^\n]*)\s*\}(\.[a-zA-Z0-9]\s*\})?'
    gr_regex = re.compile(gr_pat, (re.MULTILINE | re.VERBOSE))
    with open(infile) as f:
        # Uncomment while reading
        source = ''.join([comment_regex.sub('', line) for line in f])

    matched = []
    command = []
    options = []
    path = []
    ext = []

    for match in gr_regex.finditer(source):
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

    return matched, command, options, path, ext


def get_abspath(fn, sourcedir='.'):
    fn = op.expanduser(fn)
    if not op.isabs(fn):
        fn = op.abspath(op.join(sourcedir, fn))
    return fn


def get_implicit_ext_files(abspathroot, first=False):
    files = []
    for e in ALLOWED_EXT:
        if op.isfile(abspathroot + e) or op.islink(abspathroot + e):
            files.append(abspathroot + e)
            if first: break
    
    return files


def figs2files(sourcefile, matched, command, options, path, ext):
    """Find the filenames each include corresponds to."""
    ext_re   = re.compile(r'format\s*=\s*([a-zA-Z-0-9]+)\s*[,\]]') 
    start_re = re.compile(r'start\s*=\s*([0-9]+)\s*[,\]]') 
    end_re   = re.compile(r'end\s*=\s*([0-9]+)\s*[,\]]') 
    
    sourcedir = op.dirname(sourcefile)
    
    actual_files = []

    for i, (m,cmd,opt,p,e) in enumerate(
                                zip(matched,command,options,path,ext)):
        relp = p.replace('\\string', '').lstrip('{\t ').rstrip('}\t ')
        absp = get_abspath(relp, sourcedir)
        #print(absp)

        if cmd == 'multiinclude':
            fn_pattern = absp + '-%s'

            # Get start from options
            start_m = start_re.search(opt)
            start = int(start_m.group(1)) if start_m else 0

            # get ext
            ext_m = ext_re.search(opt)
            if ext_m:
                e = '.' + ext_m.group(1)
                fn_pattern += e
            else:
                fn_pattern.replace('-%s', '.%s')
                # That what multiinclude does.

            # get end
            end_m = end_re.search(opt)
            if end_m:
                end = int(end_m.group(1))
                filenames = [fn_pattern % number for number in range(start, end+1)]
            else:
                end = None
                filenames = set()  # /!\ different type 
                
                for fn in glob(fn_pattern % '*'):
                    number_match = re.search(fn_pattern % '(\d+)', fn)
                    if number_match and int(number_match.group(1))>=start:
                        filenames.add(fn)

            #print('ext:', e, 'start:', start, 'end:', end,
            #      'N:', len(filenames))
                
        elif cmd == 'includegraphics':
            if e:
                absp += e
            elif not p.endswith('}'):
                _, e = op.splitext(relp)
                if e and e not in ALLOWED_EXT:
                    raise ValueError('Invalid includegraphics extension %r (%s)' % (e, p))
            filenames = [absp]
        
        if not filenames:
            raise ValueError('No files for %r' % p)

        if not e:
            for fn in filenames:
                foundfiles = get_implicit_ext_files(fn)
                if not foundfiles:
                    raise ValueError('No files for %r' % fn)

                actual_files.extend(foundfiles)
        else:
            for fn in filenames:
                assert op.isfile(fn) or op.islink(fn)
            actual_files.extend(filenames)

    return sorted(set(actual_files))


def main(infile):
    figs = get_fig_list(infile)
    #print(len(figs[0]), '\n---')

    figfiles = figs2files(infile, *figs)
    print('\n'.join(figfiles))
    print("Found %d files for %d include commands" \
            % (len(figfiles),len(figs[0])),
          file=stderr)
    #print([len(s) for s in figs])


if __name__ == '__main__':
    parser = ap.ArgumentParser(description=__doc__)
    parser.add_argument('infile')
    
    args = parser.parse_args()
    main(**vars(args))

