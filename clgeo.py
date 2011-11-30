#!/usr/bin/env python

'''
a command line utility for geocoding addresses in spreadsheets
by Dan Fehrenbach, dfehrenbach@cntenergy.org

The script will...
1.open a csv or xls file at a location provided by the user
    optionally - skips header row(s) based on user input
    optionally - combines multiple columns to make a single address string based on user input
2.pass the address string to the google geocoder
3.append the geocoding result to the sheet row's existing data in a new csv sheet (sheetname_geocoded.csv)
    if an address has more than one geocode result all are printed to sheet
    if errors are encountered they will be noted on the output sheet as well

Limitations...
-requires the geopy library (installable through pip)
    http://code.google.com/p/geopy/
-google has a 2500 per day limit of addresses
    http://code.google.com/apis/maps/documentation/geocoding
'''

import os, sys, time, string, argparse, re
import csv, xlrd
from geopy import geocoders 

#import pprint
#pp = pprint.PrettyPrinter(indent=4)

#from http://stackoverflow.com/questions/1342000/how-to-replace-non-ascii-characters-in-string
def removeNonAscii(s): return "".join(i for i in s if ord(i)<128)

#used to wrap csv data object to allow to call the same functions as xlrd
class EasyCsvReader(object):
    
    def __init__(self, open_str):
        self.raw_reader = csv.reader(open(open_str, 'rb'))

        zip_sheet = zip(self.raw_reader)

        working_sheet = []
        
        for tuple_row in zip_sheet:
            working_sheet.append(tuple_row[0])

        self.easy_csv = working_sheet


    def __iter__(self):
        for row in self.easy_csv:
            yield row
        

    def row_values(self, choice_num):
        
        working_row = self.easy_csv[choice_num]
        
        return working_row


    def col_values(self, choice_num):
        
        working_col = []
        
        for row in self.easy_csv:
            working_col.append(row[choice_num])
        
        return working_col


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

parser.add_argument('--xl_name',
                    help='name of the Excel worksheet')


args = parser.parse_args()


full_file_path = os.path.abspath(args.filename)
(path, source_file) = os.path.split(full_file_path)
(file_name, file_ext) = os.path.splitext(source_file)

output_file_name = file_name + '_geocoded.csv'
output_file_path = os.path.join(path, output_file_name)


sheet_data = ''

if file_ext == '.csv':
    sheet_data = EasyCsvReader(full_file_path)
    #sheet_reader = csv.reader(open(full_file_path, 'rb'))

elif file_ext == '.xls':

    try:
        in_wb = xlrd.open_workbook(full_file_path)
    except IOError:
        print "file not found, check name and try again."
        sys.exit("exiting")

    if args.xl_name != '':
        try:
            sheet_data = in_wb.sheet_by_name(args.xl_name)
        except xlrd.biffh.XLRDError as e:
            print "bad sheet name given, trying Sheet1 default name"
            try:
                sheet_data = in_wb.sheet_by_name('Sheet1')
            except xlrd.biffh.XLRDError as e:
                print "Sheet1 didnt work either, check source workbook"
                sys.exit("exiting")

elif file_ext == '.xlsx':
    print "coming soon"
    sys.exit("exiting")
else:
    print "non spreadsheet file type, only csv, xls and xlsx work"
    sys.exit("exiting")


output_writer = csv.writer(open(output_file_path, 'wb'))


g = geocoders.Google()


line_count = 1 # set to one to make on-screen output make more sense


#the adr_loc could be a single number, but the loop below needs a list
adr_pos = args.adr_loc
if type(args.adr_loc) is not list: 
    adr_pos = [ str(args.adr_loc) ]


sheet_length = len(sheet_data.col_values(0))

#for sheet_line in sheet_data:
for row in range(args.header, sheet_length):

    line = sheet_data.row_values(row)

    adr_components = []

    for col_num, cell in enumerate(line):
        if str(col_num) in adr_pos: #col_num needs to be string to match adr_pos
            adr_components.append(str(cell)) #cell is turned into string to be cleaned

    adr_components = [re.sub('\.0','',cell) for cell in adr_components] #excel might add a .0 to zip codes
    adr_components = [c.strip() for c in adr_components] #remove extra whitespace
    adr_components = [removeNonAscii(cell) for cell in adr_components] #remove non-ascii characters
    
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
        
        #unicode issues, more cleaning needs to be done on the place string
        place = removeNonAscii(place)
        place = place.encode('ascii','ignore') 

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