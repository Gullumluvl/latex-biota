#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Convert multiline includegraphics/multiinclude statements into single line,
in a latex source file"""

#TODO: convert multiinclude into myslideshow

from sys import stderr, stdin, stdout
import re
import os.path as op
import argparse as ap
import subprocess as sp
from functools import partial
from list_latex_graphics import GR_REGEX, ALLOWED_EXT, \
                                get_abspath, \
                                parse_ext_includegraphics, \
                                get_implicit_ext_files

ITEMIZE_REGEX = re.compile(r'^(\s*)\\begin\{(itemize|enumerate)\}.*$', re.M)

ALLOWED_EXT_HTML = ['.svg', '.png', '.jpg', '.gif', '.jpeg']
ALLOWED_EXT_HTML += [_.upper() for _ in ALLOWED_EXT]

RETURN_REGEX = re.compile(r'\s*\n\s*')
PDF_REGEX = re.compile(r'\.pdf$')


def process_include_match(match, sourcedir='.'):
    # Replace path with explicit extensions and expanded shell variables.
    cmd = match.group(1)
    overlay = match.group(2)
    opts = match.group(3)
    path = match.group(4)
    ext = match.group(5)
    if ext:
        ext = ext.lstrip('}')
        path += '}'

    relp = path.replace('\\string', '').lstrip('{\t ').rstrip('}\t ')
    absp = get_abspath(relp, sourcedir)

    if cmd in ('includegraphics', 'uncovergraphics'):
        filename, ext = parse_ext_includegraphics(path, relp, absp, ext)
        if not ext or ext=='.pdf':
            try:
                filename = get_implicit_ext_files(PDF_REGEX.sub('', filename),
                                            ALLOWED_EXT_HTML+['.pdf'])[0]
            except IndexError:
                msg = 'No files for %r' % filename
                #if raise_:
                #    raise FileNotFoundError(msg)
                #else:
                print('ERROR:' + msg, file=stderr)
        #print('INFO:%r [%r]' % (filename, ext), file=stderr)
        if filename.endswith('.pdf'):  # '.eps'
            print('WARNING: Only a "pdf" found for %r. Convert with inkscape.' % relp,
                  file=stderr)
            output_svg = PDF_REGEX.sub('.svg', filename)
            assert not op.exists(output_svg)
            #r = sp.check_call(['inkscape', '-l="%s"' % output_svg, filename])
            filename = output_svg
    else:
        raise NotImplementedError('cmd=%r' % cmd)

    # convert command "uncovergraphics"
    txt = '\includegraphics' + (overlay if overlay else '') \
          + (opts if opts else '') + '{'+filename+'}'

    # drop newlines:
    return RETURN_REGEX.sub(' ', txt)


def process_source(infile):
    """"""
    sourcedir = '.' if infile is stdin else op.dirname(infile.name)
    source = infile.read()
    if not infile is stdin:
        infile.close()
    #return #ITEMIZE_REGEX.sub(r'\g<0>\n\1\\tightlist',  #NO EFFECT (yet)
    return GR_REGEX.sub(partial(process_include_match, sourcedir=sourcedir),
                        source)
    #       )


def multiinclude_to_includegraphics(source):
    raise NotImplementedError


def main():
    parser = ap.ArgumentParser(description=__doc__)
    parser.add_argument('infile', nargs='?', default=stdin,
                        type=ap.FileType('r'))
    args = parser.parse_args()
    print(process_source(args.infile))


if __name__ == '__main__':
    main()

