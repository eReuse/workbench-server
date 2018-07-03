#!/usr/bin/python3

# -*- coding: utf-8 -*-

"""
Prints tags to QL-570 with well-known working options.

More info:

- http://www.g-loaded.eu/2005/11/10/using-a-cups-printer-from-command-line/
- https://superuser.com/questions/1026576/how-to-set-the-minimum-margin-in-cups-foomatic-driver
- https://www.raspberrypi.org/forums/viewtopic.php?f=32&t=98033&p=680511s#p680511
- https://www.raspberrypi.org/forums/viewtopic.php?f=32&t=180370&p=1147727#p1147727
- https://www.raspberrypi.org/forums/viewtopic.php?t=195655
- https://www.cups.org/doc/options.html
- https://www.cups.org/doc/spec-command.html
"""

import cups
import sys
import time

import click
import click_spinner


@click.command()
@click.option('--pdf',
              type=click.Path(resolve_path=True, dir_okay=False),
              prompt='Drop the PDF file here and press ENTER:',
              help='The path of the PDF with the tags to print.')
@click.option('--printer', default='QL-570', help='The name of the printer.')
@click.option('--media', default='62x29', help='The type / size of the page.')
def print_tags(pdf: str, printer: str, media: str):
    """
    Sends to print a PDF with tags to a label printer (by default a QL-570).

    Just execute this ``python3 print_tags.py`` and drag-and-drop a
    PDF file to the terminal.
    """
    connection = cups.Connection()
    try:
        print_id = connection.printFile(printer,
                                        # Correctly parse spaces
                                        pdf.replace('\\', '').strip(),
                                        'Tags',
                                        {'media': media, 'fit-to-page': 'True'})
    except cups.IPPError as e:
        if e.args[0] == 1042:
            print('Error: the file does not exist.', file=sys.stderr)
            return 1
        else:
            raise e
    print('Printing...', end='\t')
    with click_spinner.spinner():
        while connection.getJobs().get(print_id, None) is not None:
            time.sleep(1)
    print('Done!')


if __name__ == '__main__':
    print_tags()
