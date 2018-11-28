#!/bin/python

# -*- coding: utf-8 -*-

import os
import sys
import codecs
import re

from os import listdir
from os.path import isfile, join

from wordpress_xmlrpc import Client, WordPressPost
from wordpress_xmlrpc.methods.posts import GetPosts, NewPost
from wordpress_xmlrpc.methods.users import GetUserInfo


line_terminator = ';'
#sys.stdout = codecs.getwriter('utf8')(sys.stdout)


def print_usage():
    print("Usage: " + __file__ + " -f htmls -s http://localhost/xmlrpc.php -u user -p password")
    print("       -f <folder>   Input folder. Like a 'htmls'.")
    print("       -s <server>   Wordpress server. Like a http://mysite.wordpress.com/xmlrpc.php")
    print("       -u <user>     User name")
    print("       -p <password> Password")
    print("       -d delete source file if success")

def parse_args():
    folder = ""
    server = ""
    user = ""
    password = ""
    need_delete = False

    if len(sys.argv) < 2:
        print_usage()
        exit(1)

    state = "WAIT_SWITCH"

    for arg in sys.argv[1:]:
        if state == "WAIT_SWITCH":
            if arg == "-f":
                state = "WAIT_FOLDER"

            elif arg == "-s":
                state = "WAIT_SERVER"

            elif arg == "-u":
                state = "WAIT_USER"

            elif arg == "-p":
                state = "WAIT_PASSWORD"

            elif arg == "-d":
                need_delete = True

        elif state == "WAIT_FOLDER":
            folder = arg
            state = "WAIT_SWITCH"

        elif state == "WAIT_SERVER":
            server = arg
            state = "WAIT_SWITCH"

        elif state == "WAIT_USER":
            user = arg
            state = "WAIT_SWITCH"

        elif state == "WAIT_PASSWORD":
            password = arg
            state = "WAIT_SWITCH"

        else:
            print_usage()
            exit(1)

    if  len(folder) == 0 or len(server) == 0 or len(user) == 0 or len(password) == 0:
        print_usage()

    return (folder, server, user, password, need_delete)


def get_posts(server, user, password):
    wp = Client(server, user, password)
    posts = wp.call(GetPosts())
    print(posts)

def send_post(wp, title, html):
    post = WordPressPost()
    post.title = title
    post.content = html
    post.post_status = "publish"
    post.terms_names = {
#     'post_tag': ['test', 'firstpost'],
#     'category': ['Introductions', 'Tests']
    }
    id = wp.call(NewPost(post))

    return id


def file_get_contents(filename):
    with open(filename, "r", encoding='utf8') as f:
        return f.read()


def cleanhtml(raw_html):
    cleanr = re.compile('<.*?>')
    cleantext = re.sub(cleanr, '', raw_html)
    return cleantext

#
(folder, server, user, password, need_delete) = parse_args()

onlyfiles = [f for f in listdir(folder) if isfile(join(folder, f)) and f.endswith(".html")]

try:
    wp = Client(server, user, password)
    #get_posts(server, user, password)
except Exception as e:
    print("error:", str(e).encode("utf-8"))
    exit(1)

for file in onlyfiles:
    print(file + "...", end='')
    filename, file_extension = os.path.splitext(os.path.basename(file))
    fullname = os.path.join(folder, filename + ".html")
    #title = file_get_contents(os.path.join(folder, filename + ".title"))
    html = file_get_contents(fullname)
    title = cleanhtml(html)
    title = re.sub(r"[^A-Za-z0-9 _\-\.\+\$\,\(\)]", "", title)
    title = title.strip()
    title = title[:55]

    try:
        ok = send_post(wp, title, html)
        
    #except Fault as e:
    except Exception as e:
        print("error:", str(e).encode("utf-8"))
        ok = False

    if ok:
        print("ok")
        
        if need_delete:
            os.remove(fullname)
    else:
        print("failed")

