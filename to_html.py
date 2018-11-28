#!/bin/python

# -*- coding: utf-8 -*-

import os
import sys
import codecs

global infiles, outfolder, table

def print_usage():
    print("Usage: " + __file__ + " -i file1.sql -i file2.sql -i file3.sql -o htmls -t service")
    print("       -i <file>    Input file")
    print("       -o <folder>  Output folder")
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
            if not c.isalnum() and c != "_":
                break
                
            keyword += c

            prevc = c
            c = self.fin.read(1)
            
        return (keyword, prevc, c)
        
    def read_numeric(self, prevc, c):
        value = c # [0-9]
        c = self.fin.read(1)

        while c:
            if not c.isdigit():
                break
                
            value += c

            prevc = c
            c = self.fin.read(1)
            
        return (value, prevc, c)
        
    def read_column_size(self, prevc, c):
        value = c # [0-9]
        c = self.fin.read(1)

        while c:
            if not c.isdigit() and c != ",":
                break
                
            value += c

            prevc = c
            c = self.fin.read(1)
            
        return (value, prevc, c)
        
    def read_insert_values(self, prevc, c):
        values = []
        value = ""
        
        prevc = c # (
        c = self.fin.read(1)

        while c:
            if c == "`":
                (value, prevc, c) = self.read_in_back_quotes(prevc, c)
                values.append(value)

            elif c == "'":
                (value, prevc, c) = self.read_in_single_quotes(prevc, c)
                values.append(value)

            elif c == ",":
                pass
                
            elif c == ")":
                values.append(value)
                break
            
            elif c.isdigit():
                (value, prevc, c) = self.read_numeric(prevc, c)
                values.append(value)
                continue

            prevc = c
            c = self.fin.read(1)
            
        return (values, prevc, c)
        
    def read_insert(self, prevc, c):
        result = []
        
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
        
    def get_all_backquoted(self, s):
        splited = s.split("`")
        fields = []
        
        for i,w in enumerate(splited):
            if i % 2 == 1:
                fields.append(w)
                
        return fields

    def read_create(self, prevc, c):
        result = []
        
        while c:
            if c.isalpha():
                (keyword, prevc, c) = self.read_keyword(prevc, c)
                result.append(keyword)
                continue

            if c.isnumeric():
                (numeric, prevc, c) = self.read_numeric(prevc, c)
                result.append(numeric)
                continue
            
            elif c.isspace():
                pass
                
            elif c == "`":
                (s_in_back_quotes, prevc, c) = self.read_in_back_quotes(prevc, c)
                result.append(s_in_back_quotes)
            
            elif c == "'":
                s_in_single_quotes = self.read_in_single_quotes(prevc, c)
                result.append(s_in_single_quotes)

            elif c == ",":
                result.append(c)
            
            elif c == "(":
                result.append(c)
            
            elif c == ")":
                result.append(c)
            
            elif c == ';':
                break
            
            prevc = c
            c = self.fin.read(1)

        return (result, prevc, c)
        
    def get_all_columns(self, tokens):
        result = []
        
        i = tokens.index("(") + 1
        
        while i < len(tokens):
            name = tokens[i]
            
            if name == "PRIMARY" and tokens[i+1] == "KEY":
                pass
                
            elif name == "UNIQUE" and tokens[i+1] == "KEY":
                pass

            else:
                result.append(name)

            try:
                i = tokens.index(",", i) + 1
                
                while tokens[i].isnumeric():
                    i = tokens.index(",", i) + 1

            except ValueError:
                break;                    
                    
        return result
    
    def read_token(self, table):
        s = ""      

        fields = []

        prevc = ""
        c = self.fin.read(1)

        while c:
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
                print("'" + keyword + "'")
                
                if keyword.upper() == "INSERT":
                    (tokens, prevc, c) = self.read_insert(prevc, c)
                    if tokens[1] == table:
                        if (len(tokens) > 3 and tokens[3] == "VALUES"): # INSERT INTO table () VALUES ()
                            insert_fields = tokens[2]
                            print("    columns:", insert_fields)
                            tokens = tokens[4:]
                        else: # INSERT INTO table ()
                            insert_fields = fields
                            
                        for t in tokens:
                            if isinstance(t, list):
                                self.on_insert_values(t, insert_fields)

                elif keyword.upper() == "DROP":
                    (s, prevc, c) = self.read_to_terminator(prevc, c)
                
                elif keyword.upper() == "CREATE":
                    (tokens, prevc, c) = self.read_create(prevc, c)
                    fields = self.get_all_columns(tokens)
                    print("   ", tokens[1], ":", fields)
                
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

    def on_insert_values(self, values, fields):
        global outfolder
        
        id_pos = fields.index("id")
        question_pos = fields.index("servicetext")
        answer_pos = fields.index("service_file")

        if (len(values) > max(id_pos, question_pos, answer_pos)):
            print(values[id_pos], 
                str(values[question_pos].encode("utf-8")[:25]) + "...", 
                str(values[answer_pos].encode("utf-8")[:25]) + "...")

            self.write_html(os.path.join(outfolder, values[id_pos] + ".html"),
                self.replace_special_chars(values[question_pos]) +
                '<img src="https://hwsolutiononline.com/img/banner.jpg"/><br>' +
                "<h3 class=\"widget-title\">Solution</h3>" + 
                self.replace_special_chars(values[answer_pos])
                )
        else:
            print("skip:", str(values).encode("utf-8")[:50], "can't find column")

    def replace_special_chars(self, s):
        repalce_htmls = {
            "\\r": " ",
            "\\n": " ",
        }
        
        for k,v in repalce_htmls.items():
            s = s.replace(k, v)
            
        return s
        
    def write_html(self, filename, s):
        writer = open(filename, "w", encoding="utf-8")
        writer.write(s)
        writer.close()      
    
    
#
(infiles, outfolder, table) = parse_args()

os.makedirs(outfolder, exist_ok=True)

print("Files: " + str(infiles))
for infile in infiles:
    print("Process file: " + infile)
    reader = SQLReader(infile)
    reader.read_token(table)

