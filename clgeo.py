#!/usr/bin/env python

#dfehrenbach@cntenergy.org
#
#opens as csv fill at a location provided by the user
#optionally - skips header row(s)
#optionally - combines multiple columns to make a single address string
#passess the address string to the google geocoder
#writes the geocoding result to a new csv sheet (sheetname_geocoded.csv)
# if an address has more than one geocode result all are printed to sheet
#
#google has a 2500 per day limit of addresses, so keep this in mind
# http://code.google.com/apis/maps/documentation/geocoding

import os, sys, time, string, argparse
import csv
from geopy import geocoders #http://code.google.com/p/geopy/, install available with pip

file_path = os.getcwd()

parser = argparse.ArgumentParser(description='Process addresses, retrieve lat/lon from google maps API.')

parser.add_argument('filename', help='path to a csv file of that containes some addresses')
parser.add_argument('--adr_loc', default=0, nargs='*', 
                    help='where is the address information, default is col 0, multiple columns can be defined ex adr_loc 0 1 2')
parser.add_argument('--header', default=1, type=int, help='number of header rows to skip, default is 1')

args = parser.parse_args()


sheet_reader = csv.reader(open(file_path + '/' +  args.filename, 'rb'))

name_and_ext = args.filename.split('.') #splits name around the . , use the part before the . for new file name

#output_writer = open(file_path + '/' +  name_and_ext[0] +'_geocoded.csv', 'w')
output_writer = csv.writer(open(file_path + '/' + args.filename + '_geocoded', 'wb'))

g = geocoders.Google()

line_count = 0

for line in sheet_reader:
    if line_count >= int(args.header): #if the line count is less than or equal to the header count

        adr_components = []
        send_adr = ''

        nonadr_cells = []

        for col_num, cell in enumerate(line):
            if col_num in args.adr_loc:
                adr_components.append(cell)
            else:
                nonadr_cells.append(cell)

        #for grab_cell in args.adr_loc: #loop through adr_loc numbers provided by the user, adding contents to list
        #    adr_components.append(line[int(grab_cell)])

        adr_components = [c.strip() for c in adr_components] #remove extra whitespace
        
        send_adr = ' '.join(adr_components) #join the list components with a space between each

        try:
            google_return = list(g.geocode(send_adr, exactly_one=False)) #allows for multiple results for one address
        except geocoders.google.GQueryError as e:
            err = str(e).translate(string.maketrans("",""),string.punctuation)
            error_pack = err, (0 ,0)
            google_return = error_pack,
            print "error at row " + str(line_count) + " no data found for " + str(send_adr) + ", pressing on"
        except geocoders.google.GTooManyQueriesError as e:
            err = str(e).translate(string.maketrans("",""),string.punctuation)
            error_pack = err, (0 ,0)
            google_return = error_pack,
            sys.exit("too many queries, exiting")
        except:
            err = str(sys.exc_info()[0]).translate(string.maketrans("",""),string.punctuation)
            error_pack = err, (0 ,0)
            google_return = error_pack,
            print "unknown error at row " + str(line_count) + ", " + str(send_adr) + ", pressing on"

        output_row = []

        for result in google_return:
            
            g_result = []

            place, (lat, lng) = result
            place = encode('ascii','ignore') #unicode issues, more cleaning needs to be done on the place string

            g_result = g_result.append(send_adr)
            g_result = g_result.append(place)
            g_result = g_result.append(str(len(google_return)))
            g_result = g_result.append(lat)
            g_result = g_result.append(lng)

            output_row = output_row.append(g_result)
            output_row = output_row.append(nonadr_cells)

            outputwriter.writerrow(output_row)
            #output_writer.write(send_adr + "," + str(len(google_return)) + ",%s, %.5f, %.5f" % (place, lat, lng) + "\n")
        
        time.sleep(.5) #keeps google happy

    print str(line_count) + ' row complete'
    line_count += 1