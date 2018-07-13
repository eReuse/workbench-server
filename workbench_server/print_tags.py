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

This requires Python Tkinter; in debian do ``apt install python3-tk``.
"""

import cups
import sys
import time
import tkinter
from tkinter import filedialog, messagebox


def print_tags(pdf: str, printer: str = 'QL-570', media: str = '62x29'):
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
    while connection.getJobs().get(print_id, None) is not None:
        time.sleep(0.5)
    print('Done!')


class Printer(tkinter.Frame):
    def __init__(self):
        super().__init__()
        self.master.title('Print tags')
        self.pack()
        button = tkinter.Button(self, text="Select file and print", command=self.file)
        button.grid(padx=5, pady=5)

    def file(self):
        file_path = filedialog.Open(self, filetypes=[('PDF', '*.pdf')]).show()
        if file_path:
            try:
                print_tags(file_path)
            except Exception as e:
                messagebox.showerror('Could not print', str(e))
            else:
                messagebox.showinfo('Done', 'Printed')


if __name__ == '__main__':
    top = tkinter.Tk()
    app = Printer()
    top.mainloop()
