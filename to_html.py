#!/bin/python

# -*- coding: utf-8 -*-

import os
import sys
import codecs

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
	def __init__(self, filein):
		self.fin = open(filein, "r", encoding='utf8')
		print(filein + " opened")
		
	def read_in_back_quotes(self, prevc, c):
		s = ""

		prevc = c
		c = self.fin.read(1)

		while c:
			if prevc != "\\" and c == "`":
				break
			
			s += c
			prevc = c
			c = self.fin.read(1)
		
		return (s, prevc, c)
	
	def read_in_single_quotes(self, prevc, c):
		s = ""

		prevc = c
		c = self.fin.read(1)

		while c:
			if prevc != "\\" and c == "'":
				break
			
			s += c
			prevc = c
			c = self.fin.read(1)
		
		return (s, prevc, c)
	
	def read_c_comment(self):
		s = ""
		self.prevc = "*"
		c = self.fin.read(1)

		while c:
			if c == '/' and self.prevc == "*":
				self.prevc = c
				break
			
			s += c
			self.prevc = c
			c = self.fin.read(1)
		
		return s
	
	def read_comment(self):
		s = ""		
		self.prevc = "-"
		c = self.fin.read(1)

		while c:
			if c == '\n' or c == '\r':
				self.prevc = c
				break
			
			s += c
			self.prevc = c
			c = self.fin.read(1)
		
		return s
		
	def read_keyword(self, prevc, c):
		keyword = c # alpha
		c = self.fin.read(1)

		while c:
			if not c.isalnum():
				break
				
			keyword += c

			prevc = c
			c = self.fin.read(1)
			
		return (keyword, prevc, c)
		
	def read_insert_values(self, prevc, c):
		values = []
		value = ""
		
		prevc = c
		c = self.fin.read(1)

		while c:
			if c == "'":
				(value, prevc, c) = self.read_in_single_quotes(prevc, c)
				values.append(value)

			elif c == ",":
				values.append(value)
				value = ""
				
			elif c == ")":
				break
			
			else:
				value += c

			prevc = c
			c = self.fin.read(1)
			
		return (values, prevc, c)
		
	def read_insert(self, prevc, c):
		result = []
		
		c = prevc # space
		
		while c:
			if c.isalpha():
				(keyword, prevc, c) = self.read_keyword(prevc, c)
				result.append(keyword)
				continue
			
			elif c.isspace():
				pass
				
			elif c == '`':
				(s_in_back_quotes, prevc, c) = self.read_in_back_quotes(prevc, c)
				result.append(s_in_back_quotes)
			
			elif c == "'":
				s_in_single_quotes = self.read_in_single_quotes(prevc, c)
				result.append(s_in_single_quotes)

			elif c == "(":
				(values, prevc, c) = self.read_insert_values(prevc, c)
				result.append(values)

			elif c == ",":
				result.append(",")
			
			elif c == ';':
				break
			
			prevc = c
			c = self.fin.read(1)

		return (result, prevc, c)
		
	def read_to_terminator(self, prevc, c):
		s = ""

		while c:
			if c == ";":
				break
				
			s += c

			prevc = c
			c = self.fin.read(1)
			
		return (s, prevc, c)
	
	def read_token(self, outfolder, table):
		s = ""		

		prevc = ""
		c = self.fin.read(1)

		while c:
#			print(c)
			if c == '-' and prevc == '-':
				s = self.read_comment()
				print("COMMENT: " + s[:10])
				
			elif prevc == "/" and c == '*':
				s = self.read_c_comment()
				print("C-COMMENT: " + s[:10])

			elif c == "\n":
				pass

			elif c == "\r":
				pass

			elif c.isalpha():
				(keyword, prevc, c) = self.read_keyword(prevc, c)
				print(keyword)
				
				if keyword.upper() == "INSERT":
					(tokens, prevc, c) = self.read_insert(prevc, c)
					if tokens[1] == table:
						for t in tokens:
							if isinstance(t, list):
								self.on_insert_values(outfolder, t)

				elif keyword.upper() == "DROP":
					(s, prevc, c) = self.read_to_terminator(prevc, c)
				
				elif keyword.upper() == "CREATE":
					(s, prevc, c) = self.read_to_terminator(prevc, c)
				
				elif keyword.upper() == "LOCK":
					(s, prevc, c) = self.read_to_terminator(prevc, c)
				
				elif keyword.upper() == "UNLOCK":
					(s, prevc, c) = self.read_to_terminator(prevc, c)
							
				elif keyword.upper() == "ALTER":
					(s, prevc, c) = self.read_to_terminator(prevc, c)
							
				elif keyword.upper() == "UPDATE":
					(s, prevc, c) = self.read_to_terminator(prevc, c)
							
			prevc = c
			c = self.fin.read(1)

	def on_insert_values(self, outfolder, values):
		print(str(values).encode("utf-8")[:50])

		if (len(values) > 1):
			self.write_html(os.path.join(outfolder, values[0] + ".html"),
				self.replace_special_chars(values[2]) +
				"<h3 class=\"widget-title\">Solution</h3>" + 
				self.replace_special_chars(values[4])
				)

	def replace_special_chars(self, s):
		repalce_htmls = {
			r"\r": " ",
			r"\n": " ",
		}
		
		for k,v in repalce_htmls.items():
			s = s.replace(k, v)
			
		return s
		
	def write_html(self, filename, s):
		writer = open(filename, "w", encoding="utf-8")
		writer.write('<img src="https://hwsolutiononline.com/img/banner.jpg"/>\n<br>\n')
		writer.write(s)
		writer.close()		
	
	
#
(infiles, outfolder, table) = parse_args()

os.makedirs(outfolder, exist_ok=True)

print("Files: " + str(infiles))
for infile in infiles:
	print("Process file: " + infile)
	reader = SQLReader(infile)
	reader.read_token(outfolder, table)

