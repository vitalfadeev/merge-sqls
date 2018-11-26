#!/bin/python

# -*- coding: utf-8 -*-

import os
import sys
import codecs

line_terminator = ';'
#sys.stdout = codecs.getwriter('utf8')(sys.stdout)


def print_usage():
    print("Usage: " + __file__ + " -i file1.sql -i file2.sql -i file3.sql -o htmls -t service")
    print("       -i <file>    Input file")
    print("       -o <folder   Output folder")
    print("       -t <table>   Table name")

def parse_args():
    infiles = []
    outfolder = ""
    table = ""

    if len(sys.argv) < 2:
        print_usage()
        exit(1)

    state = "WAIT_SWITCH"

    for arg in sys.argv[1:]:
        if state == "WAIT_SWITCH":
            if arg == "-i":
                state = "WAIT_FILENAME_IN"

            elif arg == "-o":
                state = "WAIT_FOLDER_OUT"

            elif arg == "-t":
                state = "WAIT_TABLENAME"

        elif state == "WAIT_FILENAME_IN":
            infiles.append(arg)
            state = "WAIT_SWITCH"

        elif state == "WAIT_FOLDER_OUT":
            outfolder = arg
            state = "WAIT_SWITCH"

        elif state == "WAIT_TABLENAME":
            table = arg
            state = "WAIT_SWITCH"

        else:
            print_usage()
            exit(1)

    if  len(infiles) == 0 or len(outfolder) == 0 or len(table) == 0:
        print_usage()

    if len(infiles) == 0:
        print("error: need -i file.sql")
        exit(1)

    if len(outfolder) == 0:
        print("error: need -o htmls")
        exit(1)

    if len(table) == 0:
        print("error: need -t table")
        exit(1)

    return (infiles, outfolder, table)




class SQLReader:
	STATE_NONE = 0
	STATE_COMMENT = 1
	STATE_KEYWORD = 3
	
	repalce_htmls = {
		r"\r": " ",
		r"\n": " ",
	}
	
	def __init__(self, filein):
		self.fin = open(filein, "r", encoding='utf8')
		print(filein + " opened")
		self.state = self.STATE_NONE
		self.prevc = ""
		
	def read_in_back_brackets(self):
		s = ""
		
		c = self.fin.read(1)

		while (c):
			if c == '`':
				s += c
				break
			
			s += c
			self.prevc = c
			c = self.fin.read(1)
		
		return s
	
	def read_in_single_brackets(self):
		s = ""
		
		c = self.fin.read(1)

		while (c):
			if c == "'" and self.prevc != "\\":
				self.prevc = c
				s += c
				break
			
			self.prevc = c
			s += c
			c = self.fin.read(1)
		
		return s
	
	def read_c_comment(self):
		s = ""
		
		c = self.fin.read(1)

		while (c):
			if c == '/' and self.prevc == "*":
				s += c
				self.prevc = c
				break
			
			s += c
			self.prevc = c
			c = self.fin.read(1)
		
		return s
	
	def read_comment(self):
		s = ""
		
		c = self.fin.read(1)

		while (c):
			if c == '\n' or c == '\r':
				s += c
				self.prevc = c
				break
			
			s += c
			self.prevc = c
			c = self.fin.read(1)
		
		return s
		
	def get_single_quoted_value(self, s):
		#print(("IN: " + s).encode('utf-8'))
		v = ""
		prevc = ""
		i = 0
		
		while i < len(s):
			if s[i]== "'" and prevc != "\\":
				return s[:i]
			
			prevc = s[i]
			i += 1
		
		return s
		
	def split_by_separator(self, s):
		splited = []
		v = ""		
		i = 0
		
		while i < len(s):
			if s[i] == ",":
				splited.append(v)
				#print(("VALUE: " + v).encode("utf-8"))
				v = ""
				i += 1

			elif s[i] == "'":
				v = self.get_single_quoted_value(s[i+1:])
				#print(("VALUE QUOTED: " + v).encode("utf-8"))
				splited.append(v)
				i += len(v) + 2 + 1
				v = ""

			else:
				v += s[i]
				i += 1

		#print(("VALUE: " + v).encode("utf-8"))
		splited.append(v)
		
		return splited
		
	def get_brackets(self, s):
		i = 0
		
		sfrom = 0
		sto = 0
		
		while i < len(s):
			if s[i] == "(":
				sfrom = i
				i += 1
				break
			
			i += 1

		while i < len(s):
			if s[i] == "'":
				#print(("PRE: " + s[i:]).encode("utf-8"))
				v = "'" + self.get_single_quoted_value(s[i+1:]) + "'"
				#print(("NOBR-VALUE: " + v).encode("utf-8"))
				i += len(v)

			elif s[i] == ")":
				sto = i
				break

			else:
				i += 1
				
		sto = i
		
		return (sfrom, sto)
		
	def replace_special_chars(self, s):
		for k,v in self.repalce_htmls.items():
			s = s.replace(k, v)
		return s
		
	def write_html(self, filename, s):
		writer = open(filename, "w", encoding="utf-8")
		# writer.write("""
# <style>
# .widget-title {
    # color: #808080;
    # font-weight: 400;
    # font-family: "PT Sans", sans-serif;
    # margin: 0 0 10px 0;
    # font-size: 16px;
    # line-height: 20px;
    # text-transform: uppercase;
    # background-color: #f5f5f5;
    # border-bottom: 2px solid #E6E6E6;
    # padding-bottom: 5px;
# }
# </style>
# """
# )
		writer.write(s)
		writer.close()		
	
	def write_title(self, filename, s):
		writer = open(filename, "w", encoding="utf-8")
		writer.write(s)
		writer.close()		
	
	def read_token(self, outfolder, table):
		s = ""		
		c = self.fin.read(1)

		while (c):
			if self.state == self.STATE_NONE:
				if c == '-' and self.prevc == '-':
					s = "-" + self.read_comment()
					#print("COMMENT: " + s[:10])
					
				elif self.prevc == "/" and c == '*':
					s = "/*" + self.read_c_comment()
					#print("C-COMMENT: " + s[:10])

				elif c in "ABCDEFGHIJKLMNOPQRSTUVWXYZ":
					self.state = self.STATE_KEYWORD;
					s = self.prevc + c

			elif self.state == self.STATE_KEYWORD:
				if c == "`":
					s += "`" + self.read_in_back_brackets()
					self.prevc = "`"
					
				elif c == "'":
					s += "'" + self.read_in_single_brackets()
					self.prevc = "'"
					
				elif c == ";":
					#s += c
					self.state = self.STATE_NONE
					s = s.lstrip();
					print("KEYWORD: " + s[:20])
					
					if s.startswith("INSERT "):
						print("INSERT")
						
						if s.startswith("INSERT INTO `" + table + "`"):
							print("INSERT INTO `" + table + "`")
							vpos = s.find("VALUES") + len("VALUES")
							values = s[vpos:]

							scan = s
							
							while scan:
								(sfrom, sto) = self.get_brackets(scan)
								unbracked_s = scan[sfrom+1: sto]
								splited = self.split_by_separator(unbracked_s)

								if (len(splited) > 1):
									print([splited[0], splited[1].encode("utf-8")])
									self.write_html(os.path.join(outfolder, splited[0] + ".html"),
										self.replace_special_chars(splited[2]) +
										"<h3 class=\"widget-title\">Solution</h3>" + 
										self.replace_special_chars(splited[4])
										)
									#self.write_title(os.path.join(outfolder, splited[0] + ".title"), splited[1])
									
								scan = scan[sto:]
					
				else:
					s += c
				
			self.prevc = c
			c = self.fin.read(1)



(infiles, outfolder, table) = parse_args()

os.makedirs(outfolder, exist_ok=True)

print("Files: " + str(infiles))
for infile in infiles:
	print("Process file: " + infile)
	reader = SQLReader(infile)
	reader.read_token(outfolder, table)
