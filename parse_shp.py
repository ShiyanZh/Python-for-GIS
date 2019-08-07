# import modules for the line length calculation, binary data unpack, and visualization.
import math
from Tkinter import *
import struct
# define point, polyline classes
class Point:
    def __init__(self, x = 0.0, y = 0.0):
        self.x = x
        self.y = y
class Polyline:
# define object initialization method partsNum
    def __init__(self, points= [], partsNum = 0):
        self.points = points
        self.partsNum = partsNum

#-----Part 1: read and process the first 100 bytes
# 1. open index file to read in binary mode
shxFile = open("Partial_Streets.shx","rb") # shapefile name can be replaced with any polyline
# 2. read index file header and interpret the meta information, e.g., bounding box, and # of #records
# read first 28 bytes
s = shxFile.read(28)
header = struct.unpack(">iiiiiii",s) # convert into 7 integers
fileLength = header[len(header)-1] # get file length, file length is the sixth element
polylineNum = (fileLength*2-100)/8 # calculate polyline numbers in the shape file based on index file length

# read other 72 bytes in header
s = shxFile.read(72)
header2 = struct.unpack("<iidddddddd",s) # convert into values and header2 will display in a tuple
print header2
minX, minY, maxX, maxY = header2[2],header2[3],header2[4],header2[5] # get boundingbox for the shape file

# 3. read records¡¯ meta information, such as offset, and content length for each record,
# define an empty list for holding offset of each feature in main file
recordsOffset = []
for i in range(0,polylineNum): # loop through each feature
    shxFile.seek(100+i*8) # jump to beginning of each record
    s = shxFile.read(4) # read out 4 bytes as offset
    offset = struct.unpack('>i',s) # find the offset of each polyline
    recordsOffset.append(offset[0]*2) # keep the offset in the list and interprete them into 8-bit
shxFile.close() # close the index file

#--------Part 2: read each polyline and prepare them in right order.
# open the main file for read in binary
shpFile = open("Partial_Streets.shp","rb") # shapefile name can be replaced with any polyline
# 4. read data dynamically based on each record content structure for specific shape types
# using offset to interprete polylines
polylines = [] # define an empty list for polylines
for offset in recordsOffset: # loop through each offset of all polylines
    shpFile.seek(offset+8+36)# jump to partsNum and pointsNum of the polyline and read them out, offset stands before the record header
    # find the partsNum and pointsNum of a polyline
    s = shpFile.read(8) 
    polyline = Polyline()# generate an empty polyline object
    partsNum, pointsNum = struct.unpack('ii',s)
    polyline.partsNum = partsNum
    print 'partsNum, pointsNum: ',partsNum, pointsNum
    # find the partsIndexing 
    s = shpFile.read(4*partsNum) # read the list of parts holding the starting sequential number of point in that part
    str = ''
    for i in range(partsNum): # finding how many partsNum we need
        str = str+'i'
    polyline.partsIndex = struct.unpack(str,s) # get the starting point number of each part and keep in a partsIndex list
    # find coordinates
    points = []
    for i in range(pointsNum): # loop through each polyline's points  
        s = shpFile.read(16)# read out polyline coordinates and add to the points' x, y coordinates' lists
        x, y = struct.unpack('dd',s)
        point = Point(x, y)#5. assemble data into objects of point, polyline, and polygon or other types.
        points.append(point)
    polyline.points = points # assign points lists to the polyline
    polylines.append(polyline) # add the polyline read to the polylines list

# create main window object
#8. Analyze and process (visualize) data as needed
root = Tk()
windowWidth, windowHeight = 800, 600 # define window size
# calculate ratios of visualization
ratiox = (maxX-minX)/windowWidth
ratioy = (maxY-minY)/windowHeight
ratio = ratiox # take the bigger ratio of window size to geographic distance
if ratioy>ratio:
    ratio = ratioy

# visualize the polylines
can = Canvas(root, width = 800, height = 600) # create canvas object
for polyline in polylines: # loop through each polyline
    xylist = [] #define an empty xylist for holding converted coordinates of every polyline
    for point in polyline.points: # loop through each point in the polyline and calculate the window coordinates, put them into xylist
        x = int((point.x-minX)/ratio)
        y = int(-(point.y-maxY)/ratio)
        xylist.append(x)
        xylist.append(y)
    
    for k in range(polyline.partsNum): #get the end sequence number of points in the part of the polyline
        if (k == polyline.partsNum-1): # eg. k=0, partsNum=1
            endPointIndex = len(polyline.points)
        else:
            endPointIndex = polyline.partsIndex[k+1]
        print endPointIndex, polyline.partsIndex # polyline.partsIndex is a tuple
    #define a temporary list for holding the part coordinates

    tempXYlist = [] #take out points' coordinates for the part and add to the temporary list
    for m in range(polyline.partsIndex[k], endPointIndex): # search the coords in every part and put them into tempXYlist
        tempX = xylist[m*2] # find the x
        tempY = xylist[m*2+1] # find the y
        tempXYlist.append(tempX)# append them into the templist
        tempXYlist.append(tempY)
    can.create_line(tempXYlist,fill='blue') # create the line
can.pack()
root.mainloop()
shxFile.close()
shpFile.close()
# close the file
