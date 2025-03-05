#!/usr/bin/env python3
''' Name of Script '''

import csv
import json
import urllib.request
import urllib.parse
from urllib.error import HTTPError
import argparse
import glob

__author__ = "Ben Mason"
__copyright__ = "Copyright 2017"
__version__ = "0.0.1"
__email__ = "locutus@the-collective.net"
__status__ = "Development"

class config:
    dispatch_url = 'http://localhost:8000/add/dispatch/'
    arrest_url = 'http://localhost:8000/add/arrest/'
    debug = False
    error_file_suffix = "error.log"
    current_error_log = ""

def write_error_log(data):

    with open(config.current_error_log, 'w+') as filehandle:
        filehandle.write(data)

def get_args():
    parser = argparse.ArgumentParser(prog='PWM Police uploader')
    
    parser.add_argument('-f', '--filename')           # positional argument
    parser.add_argument('-d', '--directory')           # positional argument
    parser.add_argument('-m', '--media', action='store_true')      # option that takes a value
    parser.add_argument('-a', '--arrest', action='store_true')      # option that takes a value

    return parser.parse_args()

def split_name(text_name):

    try:
        last, first = text_name.split(', ')
        split_first = first.split(" ")
        if len(split_first) > 1:
            first = split_first[0]
            middle = split_first[1]
        else:
            middle = ''
    
    except ValueError:
        full_name = text_name.split(' ')
        if len(full_name) < 3:
            first = full_name[0]
            last = full_name[1]
            middle = ''
        else:
            first = full_name[0]
            last = full_name[1]
            middle = full_name[2]

    name_dict = {
        'firstname' : first,
        'lastname' : last,
        'middlename' : middle
    }

    return name_dict


def read_csv_file(csv_filename):

    raw_data = []

    with open(csv_filename, newline='') as csvfile:
        call_log_csv = csv.DictReader(csvfile, delimiter=',', quotechar='"')
        raw_data = list(call_log_csv)

    return raw_data

# PD Call#,"Call Start Date & Time","Call End Date & Time",Type of Call,Street Address / Location,Officer Name
def dispatch_upload_loop(parsed_data):

    for entry in parsed_data:
        http_data = {
            'dispatch_number' : entry['PD Call#'],
            'dispatch_start' : entry['Call Start \nDate & Time'],
            'dispatch_stop' : entry['Call End \nDate & Time'],
            'dispatch_type' : entry['Type of Call'],
            'officer' : entry['Officer Name'],
            'address' : entry['Street Address / Location']
        }

        post_data(config.dispatch_url, http_data)

# Date,Arrestee Name,Age,Home City,Charge,Arrest Type,Officer Name,Violation Location
def arrest_upload_loop(parsed_data):

    for entry in parsed_data:

        arrestee_name = split_name(entry['Arrestee Name'])

        http_data = {
            'arrest_date' : entry['Date'],
            'charge' : entry['Charge'].split(";"),
            'arrest_type' : entry['Arrest Type'],
            'officer' : entry['Officer Name'],
            'address' : entry['Violation Location'],
            'arrestee' : { 
                'firstname' : arrestee_name['firstname'], 
                'lastname' : arrestee_name['lastname'], 
                'middlename' : arrestee_name['middlename'], 
                'age' : entry['Age'], 
                'home_city' : entry['Home City'] 
            },
        }

        post_data(config.arrest_url, http_data)

def post_data(url, data):

    headers = {
        "Content-Type": "application/json"
    }

    data_encoded = json.dumps(data).encode("utf-8")
    req = urllib.request.Request(url, data=data_encoded, headers=headers, method="POST")

    try:
        with urllib.request.urlopen(req) as response:
            result = response.read().decode("utf-8")
            print(".", end="")
    except HTTPError as e:
        print("X", end="")

        write_error_log(f"Error: {e.code}, {e.reason} {data_encoded}")


        if config.debug:
            print("Error:", e.code, e.reason, data)


def wrap_dispatch_upload(filename):
    csv_data = read_csv_file(filename)
    dispatch_upload_loop(csv_data)

def wrap_arrest_upload(filename):
    csv_data = read_csv_file(filename)
    arrest_upload_loop(csv_data)

def main(args):

    if args.directory:
        files = glob.glob(f"{args.directory}/*.csv")
    elif args.filename:
        files = [args.filename]

    for file in files:
        print(f'Loading file {file}: ', end="")
        config.current_error_log = f"{file}-{config.error_file_suffix}"
        if args.media:
            wrap_dispatch_upload(file)
        elif args.arrest:
            wrap_arrest_upload(file)
        else:
            print("Specify log type -m or -a")

        print("")

if __name__ == '__main__':
    args=get_args()
    main(args)