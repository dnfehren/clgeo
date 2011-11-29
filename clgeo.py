#!/usr/bin/env python

#dfehrenbach@cntenergy.org
#
#opens as csv file at a location provided by the user
#optionally - skips header row(s)
#optionally - combines multiple columns to make a single address string
#passess the address string to the google geocoder
#writes the geocoding result and all existing data to a new csv sheet (sheetname_geocoded.csv)
# if an address has more than one geocode result all are printed to sheet
# if errors are encountered they will be noted on the output sheet as well
#
#google has a 2500 per day limit of addresses, so keep this in mind
# http://code.google.com/apis/maps/documentation/geocoding

import os, sys, time, string, argparse
import csv
from geopy import geocoders #http://code.google.com/p/geopy/, install available with pip

#import pprint
#pp = pprint.PrettyPrinter(indent=4)

parser = argparse.ArgumentParser(description='Process addresses, retrieve lat/lon from google maps API.')

parser.add_argument('filename', 
                    help='path to a csv file of that containes some addresses')

parser.add_argument('--adr_loc', 
                    default=0, 
                    nargs='*',
                    dest='adr_loc',
                    help='where is the address information, default is col 0, multiple columns can be defined ex adr_loc 0 1 2')

parser.add_argument('--header', 
                    default=1, 
                    type=int, 
                    help='number of header rows to skip, default is 1')

args = parser.parse_args()


full_file_path = os.path.abspath(args.filename)
(path, source_file) = os.path.split(full_file_path)
(file_name, file_ext) = os.path.splitext(source_file)

output_file_name = file_name + '_geocoded' + file_ext
output_file_path = os.path.join(path, output_file_name)


sheet_reader = csv.reader(open(full_file_path, 'rb'))
output_writer = csv.writer(open(output_file_path, 'wb'))


g = geocoders.Google()


line_count = 1 # set to one to make on-screen output make more sense


#the adr_loc could be a single number, but the loop below needs a list
adr_pos = args.adr_loc
if type(args.adr_loc) is not list: 
    adr_pos = [ str(args.adr_loc) ]

for line in sheet_reader:
     #if the line count is less than or equal to the header count
    if line_count >= int(args.header) + 1: #the '+ 1' is there because the line_count starts at 1 not 0

        adr_components = []

        for col_num, cell in enumerate(line):
            if str(col_num) in adr_pos:
                adr_components.append(cell)

        adr_components = [c.strip() for c in adr_components] #remove extra whitespace
        
        send_adr = ' '.join(adr_components) #join the list components with a space between each

        try:
            google_return = list(g.geocode(send_adr, exactly_one=False)) #allows for multiple results for one address
        
        except geocoders.google.GQueryError as e:
            #on an error a fake google return package is created to feed the output writing steps
            err = str(e).translate(string.maketrans("",""),string.punctuation) #no punctuation in csv cell
            error_pack = err, (0 ,0) #error string plus a 0 for lat and long in a tuple
            google_return = error_pack, #adds the tuple to the list? right?
            print "error at row " + str(line_count) + " no data found for " + str(send_adr) + ", pressing on"
        except geocoders.google.GTooManyQueriesError as e:
            err = str(e).translate(string.maketrans("",""),string.punctuation)
            error_pack = err, (0 ,0)
            google_return = error_pack,
            sys.exit("too many queries, exiting") #exits out if too many queries, wait til tomorrow or try a longer delay
        except:
            err = str(sys.exc_info()[0]).translate(string.maketrans("",""),string.punctuation)
            error_pack = err, (0 ,0)
            google_return = error_pack,
            print "unknown error at row " + str(line_count) + ", " + str(send_adr) + ", pressing on"

        for result in google_return:
            
            g_result = []

            place, (lat, lng) = result
            place = place.encode('ascii','ignore') #unicode issues, more cleaning needs to be done on the place string

            g_result.append(send_adr) #the raw address that was sent to google
            g_result.append(place) #the place address that was returned from google

            if lat == 0: 
                #if lat is 0 then there was probably an error in the API processing
                # note that in the output
                g_result.append('error')
            elif not place[0].isdigit():
                #if the returned place name doesnt start with a number its probably
                # a general place returned as the closest match, this should be noted
                g_result.append('potential_error')    
            else:
                #otherwise output how many results come back for that address
                # 1 should be the standard
                # if its more than 1 the rows could use some better grouping, maybe some kind of unique id
                g_result.append(str(len(google_return)))
            
            g_result.append(lat) #the lattitute from google
            g_result.append(lng) #the longitude from google

            output_row = line + g_result #add the result data to the end of the source data

            output_writer.writerow(output_row)

        time.sleep(.5) #keeps google happy

    print str(line_count) + ' row complete'
    line_count += 1