#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Convert "columns" and "block" environments to the correct
fenced divs with attributes (for revealjs slides)."""


from sys import stdin
import re
import argparse as ap

# See Beamer manual:
COLUMNS_OPTIONS = ['b', 'c', 'onlytextwidth', 't', 'T', 'totalwidth=.*']

# Assume one command per line.
COLUMNS_REGEX = re.compile(r'^\s*\\begin\{columns\}(\[[^[]]+\])?')
COLUMN_REGEX = re.compile(r'^\s*\\begin\{column\}(\[[^[]]+\])?\{(.+)\}')
BLOCK_REGEX = re.compile(r'^\s*\\begin\{(alert|example|)block\}\{(.*)\}')

END_REGEX = re.compile(r'^\s*\\end\{((?:alert|example|)block|columns?)\}')

WIDTH_REGEX = re.compile(r'([0-9]*(?:\.[0-9]*)?)(.*)')
#TODO: notes

def width2html(width_str):
    width, unit = WIDTH_REGEX.match(width_str.strip()).groups()
    if unit in (r'\textwidth', r'\linewidth'):
        width = float(width)*100
        unit = r'\%'

    return '%g' % width + unit


def process_source(infile):
    for line in infile:
        if COLUMNS_REGEX.match(line):
            options = COLUMNS_REGEX.match(line).groups()
            print(r':::::: {.columns options="%s"}' % options)
        
        elif COLUMN_REGEX.match(line):
            placement, width_str = COLUMN_REGEX.match(line).groups()
            print(r'::: {.column width="%s" placement="%s"}'
                    % (width2html(width_str), placement))
        
        elif BLOCK_REGEX.match(line):
            blocktype, title = BLOCK_REGEX.match(line).groups()
            # Convention that slide-level=2
            if blocktype == '':
                print(r'\subsubsection{%s}' % title)
            elif blocktype == 'alert':
                print(r'### %s {.alert}' % title)
            elif blocktype == 'example':
                print(r'### %s {.example}' % title)
            else:
                raise ValueError('Block type "%s" not understood' % blocktype)

        elif END_REGEX.match(line):
            environment = END_REGEX.match(line).group(1)
            if environment == 'columns':
                print(r'::::::')
            elif environment == 'column':
                print(r':::')
            else:
                # Block environment begins as a lower level section.
                pass
        else:
            print(line.rstrip())

    #if not infile is stdin:
    #    infile.close()


def main():
    parser = ap.ArgumentParser(description=__doc__)
    parser.add_argument('infile', nargs='?', default=stdin,
                        type=ap.FileType('r'))
    args = parser.parse_args()
    print(process_source(args.infile))


if __name__ == '__main__':
    main()
