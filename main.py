#!?bin/python

import os, os.path, sys


def remove_old_outfile(outfile):
    if os.path.isfile(outfile):
        os.remove(outfile)

def  is_insert(line):
    # INSERT INTO `table`
    # (...);
    if line.startswith("INSERT INTO `" + table + "`"):
        return True

    return False

def is_last_value(line):
    if line.endswith(";\n"):
        return True

    return False

def init_outfile(infiles, outfile, table):
    with open(outfile, "a") as fout:
        fout.write("-- Merged from: " + str(infiles) + "\n")
        fout.write("-- Merged table: " + table + "\n")
        fout.write("""
SET SQL_MODE = "NO_AUTO_VALUE_ON_ZERO";
SET time_zone = "+00:00";

/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET @OLD_CHARACTER_SET_RESULTS=@@CHARACTER_SET_RESULTS */;
/*!40101 SET @OLD_COLLATION_CONNECTION=@@COLLATION_CONNECTION */;
/*!40101 SET NAMES utf8mb4 */;

""")

def one_file(infile, outfile):
    state = "SEARCH_INSERT"

    with open(outfile, "a") as fout:
        with open(infile) as fin:
            for line in fin:
                if state == "SEARCH_INSERT":
                    if is_insert(line):
                        fout.write(line)
                        state = "SEARCH_VALUES"
                        continue

                elif state == "SEARCH_VALUES":
                    fout.write(line)
                    if is_last_value(line):
                        state = "SEARCH_INSERT"

def merge_sql(infiles, outfile, table):
    for infile in infiles:
        one_file(infile, outfile)

def print_usage():
    print("Usage: " + __file__ + " -i file1.sql -i file2.sql -i file3.sql -o outfile.sql -t service")

def parse_args():
    infiles = []
    outfile = ""
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
                state = "WAIT_FILENAME_OUT"

            elif arg == "-t":
                state = "WAIT_TABLENAME"

        elif state == "WAIT_FILENAME_IN":
            infiles.append(arg)
            state = "WAIT_SWITCH"

        elif state == "WAIT_FILENAME_OUT":
            outfile = arg
            state = "WAIT_SWITCH"

        elif state == "WAIT_TABLENAME":
            table = arg
            state = "WAIT_SWITCH"

        else:
            print_usage()
            exit(1)

    if  len(infiles) == 0 or len(outfile) == 0 or len(table) == 0:
        print_usage()

    if len(infiles) == 0:
        print("error: need -i file.sql")
        exit(1)

    if len(outfile) == 0:
        print("error: need -o outfile.sql")
        exit(1)

    if len(table) == 0:
        print("error: need -t table")
        exit(1)

    return (infiles, outfile, table)


# main
(infiles, outfile, table) = parse_args()
remove_old_outfile(outfile)
init_outfile(infiles, outfile, table)
merge_sql(infiles, outfile, table)
