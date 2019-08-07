#%%
#SET UP PART   SET UP PART   SET UP PART   SET UP PART   SET UP PART   SET UP PART   SET UP PART
#SET UP PART   SET UP PART   SET UP PART   SET UP PART   SET UP PART   SET UP PART   SET UP PART 
import Tkinter
import struct
import networkx as nx
import math
import os
from osgeo import ogr
from arcpy import *

#Set up the file path for varoous files. filename for Road, riverpath for river
cwd = "D:\\GWU\\Intro_GIS_program\\ggs650_projectOp1_ShiyanZhang\\"
arcpy.env.workspace = cwd
arcpy.env.overwriteOutput = True
filename = cwd + "main_road_separte"
riverpath = cwd + "rivers_1"

# Set up a class called polyline, will be used when reading shp file
class Polyline:
    def __init__(self, points= [], partsNum = 0):
        self.points = points
        self.partsNum = partsNum
# Set up point class, for reading shp and calculate the intersection
class Point:
    def __init__(self, x = 0.0, y = 0.0):
        self.x = float(x)
        self.y = float(y)
# Set up a linesegment class, it represent each segment within a polyline, it will used when 
# finding intersection        
class lineSegment:
    def __init__(self, p1=Point(), p2=Point()):
        self.p1,self.p2  = p1,p2
    def overlap(self, lineSeg):
        small = min(self.p1.y, self.p2.y)
        big = max(self.p1.y, self.p2.y)
        if small<lineSeg.p1.y<big or small<lineSeg.p2.y<big:
            return 1
        else:
            return -1
    ## If two lines are parallel but not overlap return 0, overlap return 1
    ## intersect reture inersection point, otherwise return -1         
    def intersect(self, lineSeg):
        if self.p1.x == self.p2.x: ## self parallel to y
             if lineSeg.p1.x == lineSeg.p2.x and lineSeg.p1.x == self.p1.x:
                 return self.overlap(lineSeg)
             else:
                 ## Calcuate the y0 based on y = a2x + b2
                 if (lineSeg.p2.x-lineSeg.p1.x) == 0:
                     a2 = (lineSeg.p2.y-lineSeg.p1.y)/((lineSeg.p2.x-lineSeg.p1.x)+0.000000000000000000000001);
                 else:
                     a2 = (lineSeg.p2.y-lineSeg.p1.y)/(lineSeg.p2.x-lineSeg.p1.x)
                 b2 = lineSeg.p2.y -  a2*lineSeg.p2.x
                 x0 = self.p1.x
                 y0 = a2 * x0 + b2
        else: ## self is not parallel to y
             ## Check if otherlineSegment is parallel to y
            if lineSeg.p1.x == lineSeg.p2.x: ## Parallel to y
                 ## Calcaulate a1 and b1
                 a1 = (self.p2.y - self.p1.y)/(self.p2.x - self.p1.x)
                 b1 = self.p1.y -  a1*self.p1.x
                 #print "a1 and b1 is : ", a1, b1
                 x0 = lineSeg.p1.x
                 y0 = a1 * x0 + b1
            else:
                 ## Calculate a1,b1,a2,b2                
                 a1 = (self.p2.y-self.p1.y)/(self.p2.x-self.p1.x)
                 b1 = self.p2.y -  a1*self.p2.x
                 a2 = (lineSeg.p2.y-lineSeg.p1.y)/(lineSeg.p2.x-lineSeg.p1.x)
                 b2 = lineSeg.p2.y -  a2*lineSeg.p2.x
                 if a1 == a2: 
                     if b1 == b2: ## check if two lines overlaps
                         return self.overlap(lineSeg) 
                     else: ## two lines are parallel
                         return 0
                 else:                      
                     x0 = (b1 - b2)/(a2 - a1)
                     y0 = a1 * x0 + b1                     
        # check if x0 belongs to [x1,x2] and [x3,x4], y0 belongs to [y1, y2] and [y3,y4]
        if((self.p1.x - x0)*(x0-self.p2.x)>=0 \
           and (lineSeg.p1.x-x0)*(x0-lineSeg.p2.x)>=0\
           and (self.p1.y-y0)*(y0-self.p2.y)>=0 \
           and (lineSeg.p1.y-y0)*(y0-lineSeg.p2.y)>=0):
             print "x0 and y0 belongs two line segment : ", x0, y0
             return Point(x0, y0)
        else:
            return -1

# define a function to calculate euclidean distance between two points
def Eucl(x1, y1, x2, y2):
        distance = math.sqrt((x1-x2)**2 + (y1-y2)**2)
        return distance
#%%
#FUNCTION PART  FUNCTION PART  FUNCTION PART  FUNCTION PART  FUNCTION PART  FUNCTION PART
#FUNCTION PART  FUNCTION PART  FUNCTION PART  FUNCTION PART  FUNCTION PART  FUNCTION PART
#
# STlist stands for the list of pairs of coordinate when you click on the screen
# It will be transformed into real-world coordinate by a formula. This formula is
# the reverse formula for formula used in reading a shp
global STlist
STlist = []
#This callback function record the mouse coordinate when clicking on the screen, then append the 
#coordinates to STlist, then draw a red point over the place
def callback(event):
    a = (event.x, event.y)
    STlist.append(a)
    canvas.create_oval(event.x-5, event.y-5, event.x+5, event.y+5, fill = "red")
    return STlist

#This function will reset all gobal list back to empty, and also delete all canvas drawing
def cleanscreen():
    print"cleaning"
    global STlist
    STlist = []
    canvas.delete('all')
    global Riverlist
    global Roadlist
    Riverlist=[]
    Roadlist=[]
    return STlist
    
#If the STlist have at least 2 element, it means at least we can generate one shortest path
#Then initialize this function, otherwise just tell user points are not enough
def shortestpath(STlist, filename, cwd):
    if len(STlist) >= 2:
        #SETup part for this function, it read in the the road shapefile, but only store four bounding
        #box value
        shxFile = open(filename+".shx","rb")
        s = shxFile.read(28)
        header = struct.unpack(">iiiiiii",s) # convert into 7 integers
        s = shxFile.read(72)
        header2 = struct.unpack("<iidddddddd",s)
        minX, minY, maxX, maxY = header2[2],header2[3],header2[4],header2[5]
        Arcxylist = []
        windowWidth, windowHeight = 800, 600 # define window size
        #calculate the ratio, same as 'openFile' function
        ratiox = (maxX-minX)/windowWidth
        ratioy = (maxY-minY)/windowHeight
        ratio = ratiox 
        if ratioy>ratio:
            ratio = ratioy
        dsc = arcpy.Describe(filename+".shp")
        coord_sys = dsc.spatialReference
        #The for loop below will convert Tkinter coordinates into Arcgis-real-world coorinates
        for i in range(1,len(STlist), 2):
            Arcxylist.append([minX+STlist[i-1][0]*ratio, maxY-STlist[i-1][1]*ratio])#[minX + source.x* ratio, maxY + source.y* ratio]
            Arcxylist.append([minX+STlist[i][0]*ratio, maxY-STlist[i][1]*ratio])
            #set up a relative small distance to compare
            minD = 10000000
            minD2 = 10000000
            G = nx.read_shp("main_road_separte.shp")
            Conlist = list(nx.connected_component_subgraphs(G.to_undirected()))
            g = Conlist[0]
            nodelist = g.nodes(data=True)
            nodelist2 = g.nodes(data=True)
            source = target = ()
            for nodes in nodelist:
                distance = Eucl(nodes[0][0], nodes[0][1], Arcxylist[i-1][0], Arcxylist[i-1][1])
                if distance < minD:
                    minD = distance
                    source = nodes[0]
            for nodes2 in nodelist2:
                distance2 = Eucl(nodes2[0][0], nodes2[0][1], Arcxylist[i][0], Arcxylist[i][1])
                if distance2 < minD2:
                    minD2 = distance2
                    target = nodes2[0]
            result_graph = g.subgraph(nx.shortest_path(g, source, target))
            directory = cwd+"sss"+"a"*i
            if not os.path.exists(directory):
                os.makedirs(directory)
            nx.write_shp(result_graph, directory)
            arcpy.DefineProjection_management(directory+"\\edges.shp", coord_sys)
            openFile(directory+"\\edges.shx", directory+"\\edges.shp", "black")
    else:
        print "Selected Points not enough"

Riverlist = []
Roadlist = []

def checkintersect(Riverlist, Roadlist):
    lineseglist1 = []
    lineseglist2 = []
    for poly in Riverlist:
        for i in range(3, len(poly), 2):
            point1 = Point(poly[i-3], poly[i-2])
            point2 = Point(poly[i-1], poly[i])
            lineseg1 = lineSegment(point1, point2)
            lineseglist1.append(lineseg1)
    for poly2 in Roadlist:
        for i in range(3, len(poly2), 2):
            point1 = Point(poly2[i-3], poly2[i-2])
            point2 = Point(poly2[i-1], poly2[i])
            lineseg2 = lineSegment(point1, point2)
            lineseglist2.append(lineseg2)
    for River in lineseglist1:
        for Road in lineseglist2:
            result = River.intersect(Road)
            if type(result) == int:
                continue
            else:
                canvas.create_oval(result.x-3, result.y-3, result.x+3, result.y+3, fill="cyan")
                canvas.create_line(River.p1.x, River.p1.y, River.p2.x, River.p2.y, width=2, fill="magenta")
                canvas.create_line(Road.p1.x, Road.p1.y, Road.p2.x, Road.p2.y, width=1, fill="magenta")
                

      
def openFile(shx,shp,color):
    global Riverlist
    global Roadlist
    shxFile = open(shx,"rb")
    s = shxFile.read(28)
    header = struct.unpack(">iiiiiii",s) # convert into 7 integers
    fileLength = header[len(header)-1] # get file length, file length is the sixth element
    polylineNum = (fileLength*2-100)/8

    s = shxFile.read(72)
    header2 = struct.unpack("<iidddddddd",s)
    #print header2
    if shx[-9:] == "edges.shx":
        minX, minY, maxX, maxY = -2163878.18071492, -1375013.517113749, 1990928.239871636, 1223574.9521798939
    else:
        minX, minY, maxX, maxY = header2[2],header2[3],header2[4],header2[5]
    #Minmaxlist = [minX, minY, maxX, maxY]

    recordsOffset = []
    for i in range(0,polylineNum): # loop through each feature
        shxFile.seek(100+i*8) # jump to beginning of each record
        s = shxFile.read(4) # read out 4 bytes as offset
        offset = struct.unpack('>i',s) # find the offset of each polyline
        recordsOffset.append(offset[0]*2) # keep the offset in the list and interprete them into 8-bit
    shxFile.close()

    shpFile = open(shp,"rb")
    polylines = [] # define an empty list for polylines
    for offset in recordsOffset: # loop through each offset of all polylines
        shpFile.seek(offset+8+36)
        s = shpFile.read(8) 
        polyline = Polyline()# generate an empty polyline object
        partsNum, pointsNum = struct.unpack('ii',s)
        polyline.partsNum = partsNum
        s = shpFile.read(4*partsNum) 
        str = ''
        for i in range(partsNum): # finding how many partsNum we need
            str = str+'i'
        polyline.partsIndex = struct.unpack(str,s) 
    # find coordinates
        points = []
        for i in range(pointsNum): # loop through each polyline's points  
            s = shpFile.read(16)
            x, y = struct.unpack('dd',s)
            point = Point(x, y)
            points.append(point)
        polyline.points = points # assign points lists to the polyline
        polylines.append(polyline)
        
    windowWidth, windowHeight = 800, 600 # define window size
    ratiox = (maxX-minX)/windowWidth
    ratioy = (maxY-minY)/windowHeight
    ratio = ratiox 
    if ratioy>ratio:
        ratio = ratioy

    for polyline in polylines: 
        xylist = [] 
        for point in polyline.points: 
            x = int((point.x-minX)/ratio)
            y = int(-(point.y-maxY)/ratio)
            xylist.append(x)
            xylist.append(y)
        for k in range(polyline.partsNum): #get the end sequence number of points in the part of the polyline
            if (k == polyline.partsNum-1): # eg. k=0, partsNum=1
                endPointIndex = len(polyline.points)
            else:
                endPointIndex = polyline.partsIndex[k+1]
            #print endPointIndex, polyline.partsIndex
        tempXYlist = [] #take out points' coordinates for the part and add to the temporary list
        for m in range(polyline.partsIndex[k], endPointIndex): # search the coords in every part and put them into tempXYlist
            tempX = xylist[m*2] # find the x
            tempY = xylist[m*2+1] # find the y
            tempXYlist.append(tempX)# append them into the templist
            tempXYlist.append(tempY)
        if color == "orange":
            Roadlist.append(tempXYlist)
        if color == "blue":
            Riverlist.append(tempXYlist)
        canvas.create_line(tempXYlist,fill=color)
        #print tempXYlist
    shxFile.close()
    shpFile.close()

def Zoomin():
    canvas.scale("all", 0, 0, 2.0, 2.0)
def Zoomout():
    canvas.scale("all", 0, 0, 0.5, 0.5)
def Mleft(event):
    canvas.xview_scroll(-1, "units")
def Mright(event):
    canvas.xview_scroll(1, "units")
def Mup(event):
    canvas.yview_scroll(-1, "units")
def Mdown(event):
    canvas.yview_scroll(1, "units")
#%%
    
win = Tkinter.Tk()
win.title('Mini GIS')
win.bind('<Left>', Mleft)
win.bind('<Right>', Mright)
win.bind('<Up>', Mup)
win.bind('<Down>', Mdown)
canvas = Tkinter.Canvas(win, bg='white', height = 600, width = 800)
canvas.bind("<Button-1>", callback)
canvas.pack(side=Tkinter.LEFT)
frame = Tkinter.Frame(win)

roads = Tkinter.Button(frame, width = 15,text= 'Show Roads',fg="blue", 
                     command=lambda: openFile(filename+".shx", filename+".shp", "orange"))
river = Tkinter.Button(frame, width = 15,text= 'Show Rivers',fg="blue", 
                     command=lambda: openFile(riverpath+".shx", riverpath+".shp", "blue"))
checkIn = Tkinter.Button(frame, width = 15,text= 'Check Intersection',fg="blue",
                          command=lambda: checkintersect(Riverlist, Roadlist))                   
shortest = Tkinter.Button(frame, width = 15,text= 'Shortest Path',fg="blue",
                          command=lambda: shortestpath(STlist, filename, cwd))
reset = Tkinter.Button(frame, width = 15,text= 'Reset',fg="blue",
                          command=lambda: cleanscreen())
zoomin = Tkinter.Button(frame, width = 15,text= 'Zoom In',fg="blue", command=lambda: Zoomin())
zoomout = Tkinter.Button(frame, width = 15,text= 'Zoom Out',fg="blue", command=lambda: Zoomout())




roads.pack()
river.pack()
checkIn.pack()
shortest.pack()
reset.pack()
zoomin.pack()
zoomout.pack()
frame.pack(side=Tkinter.RIGHT, fill = Tkinter.BOTH)

win.mainloop()

