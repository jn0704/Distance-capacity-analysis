import osmnx as ox
import networkx as nx
import matplotlib.pyplot as plt
import pandas as pd
from osgeo import ogr
import json
from networkx.readwrite import json_graph

"""
In this cell, we read shapefiles for the anlaysis and check the information
"""
### Road files and read information

## read shapefiles
pop_ds = ogr.Open('population point layer.shp')
pop_lyr = pop_ds.GetLayer()
shelter_ds = ogr.Open('shelter location point layer.shp')
shelter_lyr = shelter_ds.GetLayer()
road_ds = ogr.Open('road network line layer.shp')
road_lyr = road_ds.GetLayer()

## Get field name of road network
rfn = [] #road field name
road_field = road_lyr.GetLayerDefn()
for n in range(road_field.GetFieldCount()) :
        name = road_field.GetFieldDefn(n).name
        rfn.append(name)
rfn.append('Y')
rfn.append('X')

## Get field name and type of pop layer
pfn = [] #road field name
pop_field = pop_lyr.GetLayerDefn()
for n in range(pop_field.GetFieldCount()) :
        name = pop_field.GetFieldDefn(n).name
        pfn.append(name)

## Get field name of shelter layer
sfn = [] #road field name
shelter_field = shelter_lyr.GetLayerDefn()
for n in range(shelter_field.GetFieldCount()) :
        name = shelter_field.GetFieldDefn(n).name
        sfn.append(name)
"""
In this cell, we create a dataset for the analysis
The algorithm converts the shapefiles into a graph and a set of dataframes
If we have done this part before, we do not have to do this
"""
### Create a graph from road network
### Create dictionaries for refering node's coordinates

## create empty graph
G = nx.Graph()

## Create data frame for saving road information
road_df = pd.DataFrame(columns=['START_NODE', 'END_NODE', 'COORDINATES', 'LEN', 'HAZARD'])

## Prepare empty dataset to save an information
dict_coorToNum = {} # the dictionary to find a node number from coordinates
dict_numToCoor = {} # the dictionary to find a coordinates from a node number
key = 0 # row of matrix
value = 0 # column of matrix
num = 0

## add node and edge in the enpy graph
for feat in road_lyr : # call features from a road mayer
    geom = feat.geometry() # get a geometry from the feature
    if geom is None :
        continue
    attr = [] #attributes
    l = geom.GetPointCount() # get the number of points of each line
    x_start = geom.GetX(0) # get the first and last points' coordinates of line
    x_end = geom.GetX(l-1)
    y_start = geom.GetY(0)
    y_end = geom.GetY(l-1)
    start = str(x_start)+','+str(y_start) # combine the coordinates to save as string
    end = str(x_end)+','+str(y_end)
    # if the node (coordinates) is new in the matrix, add it in the matrix
    if start not in list(dict_coorToNum.keys()) :
        dict_coorToNum[start] = key # and save the information in the dictionaries
        dict_numToCoor[key] = start
        key += 1 # and add the key number
    if end not in list(dict_coorToNum.keys()) :
        dict_coorToNum[end] = key
        dict_numToCoor[key] = end
        key += 1
    length = feat.GetField('LEN')
    hazard = feat.GetField('HAZARD')
    f_id = feat.GetField('NUM')
    # add the edge in the matrix
    G.add_edge(dict_coorToNum[start], dict_coorToNum[end], fid = f_id, LEN = length, HAZARD = hazard, 
               START= (y_start, x_start), END=(y_end, x_end))
    # get the coordinates of all points of line feature
    geom_list = [] 
    for i in range(geom.GetPointCount()) : # call the coordiantes and concatnate them as a string to save
        geom_list.append(str(geom.GetY(i)) + ',' + str(geom.GetX(i)))
    geoms = '|'.join(geom_list)
    # add coordinates information in the data frame
    row = [dict_coorToNum[start], dict_coorToNum[end], geoms, length, hazard]
    road_df.loc[num] = row
    if num % 500 == 0 :
        print(row)
    num += 1

"""
In this cell, we save the results of above cell
"""
## Save the dictionaris as json files
json_dict_coorToNum = json.dumps(dict_coorToNum)
f = open('.json', 'w')
f.write(json_dict_coorToNum)
f.close()

json_dict_numToCoor = json.dumps(dict_numToCoor)
f = open('.json', 'w')
f.write(json_dict_numToCoor)
f.close()

road_df.to_json('.json')

## Save the graph into a json file
js_graph = json.dumps(json_graph.node_link_data(G))
f = open('.json', 'w')
f.write(js_graph)
f.close()

"""
Notice!
If we already have dataset as jsonfiles, we just read these files
"""
# read data for analysis
dict_coorToNum = json.load(open(
    '.json'))
dict_numToCoor = json.load(open(
    '.json'))
js_G = json.load(open(
    '.json', "r"))
G = json_graph.node_link_graph(js_G)


"""
In this cell, we convert the shapefiles into lists of start and end nodes
The data saves their coordinates, id, and population number, and capacity area
"""
## Get start node information (pop)
total_pop = 0
pop_point = []
for feat in pop_lyr :
    geom = feat.geometry()
    x = geom.GetX()
    y = geom.GetY()
    coor = str(x)+','+str(y)
    pid = int(feat.GetField('PID'))
    pop = feat.GetField('TMST_20_su')
    if pop is None :
        total_pop += float(0)
        pop_point.append([coor, pid, 0])
    else :
        total_pop += float(pop)
        pop_point.append([coor, pid, pop])
  

## Get end node information (shelter)
total_cap = 0
shel_point = []
for feat in shelter_lyr :
    geom = feat.geometry()
    x = geom.GetX()
    y = geom.GetY()
    coor = str(x)+','+str(y)
    sid = int(feat.GetField('SID'))
    cap = feat.GetField('AREA')
    if cap is None :
        total_cap += float(0)
        shel_point.append([coor, sid, 0])
    else :
        total_cap += float(cap)
        shel_point.append([coor, sid, cap])
        
"""
The first module calculates the shortest path between population point and shleter point.
The length of the dataframe is the product of the number of population and shelter.
The dataframe saves id of population and shelter, population number, shleter capacity, and costs.
"""
## Create a empty dataframe
shortest_df = pd.DataFrame(columns=['POP_ID', 'SHELTER_ID', 'POP_NODE', 'SHELTER_NODE', 
                                    'POP', 'CAP', 'LEN', 'HAZARD'])

## Start creating matrix
num = 0
for pop in pop_point :
    ## load population information
    pop_node = dict_coorToNum[pop[0]]
    pop_id = pop[1]
    pop_num = pop[2]
    for shelter in shel_point :
        ## load shelter information
        shelter_node = dict_coorToNum[shelter[0]]
        shelter_id = shelter[1]
        shelter_cap = shelter[2]
        ## calculate the shortest path
        shortest_path = nx.dijkstra_path(G, pop_node, shelter_node, weight='LEN')
        shortest_len = nx.shortest_path_length(G, pop_node, shelter_node, weight='LEN')
        shortest_hazard = 0
        for i in range(0, len(shortest_path)-1) :
            shortest_hazard += G[shortest_path[i]][shortest_path[i+1]]['HAZARD']
        row = [pop_id, shelter_id, pop_node, shelter_node, pop_num, 
               shelter_cap, shortest_len, shortest_hazard]
        shortest_df.loc[num] = row
        num += 1
        if num % 500 == 0 :
            print(num)
            
## save the results
shortest_df.to_json('.json')
shortest_df.to_csv('.csv')

"""
Notice!
If we have already the results of the first and second module, we just read the files
"""
shortest_df = pd.read_json('.json')

"""
The third module assigns population to shleter. First, the module assigns population to shleter
that has the shortest route between them. If the capacity of shelter is full, the module assigns population
to the shelter that has the next shortest route.
In addition, when the algorithm assigns population, it creates evacuation route feature in a shapefile
to visualize the routes.
"""
"""
First, we analyze the matrix that uses only the shortest path.
"""
## Assings the matrix considering only the shortest path
## Convert dataframe for analysis
shortest_df['ASSIGN'] = 0
pop_df = shortest_df.drop_duplicates('POP_ID', keep='first')
shel_df = shortest_df.drop_duplicates('SHELTER_ID', keep='first')
pop_df.reset_index(drop=True, inplace=True)
shel_df.reset_index(drop=True, inplace=True)
shortest_df['POP_COPY'] = shortest_df['POP']
shortest_df['CAP_COPY'] = shortest_df['CAP']

## get column index
pop_id_index = list(shortest_df.columns).index('POP_ID')
shel_id_index = list(shortest_df.columns).index('SHELTER_ID')
pop_node_index = list(shortest_df.columns).index('POP_NODE')
shel_node_index = list(shortest_df.columns).index('SHELTER_NODE')
pop_index = list(shortest_df.columns).index('POP')
cap_index = list(shortest_df.columns).index('CAP')
assign_index = list(shortest_df.columns).index('ASSIGN')
pop_copy_index = list(shortest_df.columns).index('POP_COPY')
cap_copy_index = list(shortest_df.columns).index('CAP_COPY')

## Create shapefile
driver = ogr.GetDriverByName('ESRI Shapefile')
data_source = driver.CreateDataSource('.shp')
create_lyr = data_source.CreateLayer('shortest_path', road_lyr.GetSpatialRef(), ogr.wkbMultiLineString)
data_source.Destroy()

## Create shortest path as linestring
## read shapefile
path_ds = ogr.Open('.shp', 1)
path_lyr = path_ds.GetLayer('shortest_path')
path_defn = path_lyr.GetLayerDefn()
print(path_lyr.GetGeomType() == ogr.wkbLineString)

## set field
field_name = ['POP_ID', 'SHEL_ID', 'POP_NODE', 'SHEL_NODE', 'POP', 'CAP', 'LEN', 'HAZARD']
path_lyr.CreateField(ogr.FieldDefn('POP_ID', ogr.OFTInteger))
path_lyr.CreateField(ogr.FieldDefn('SHEL_ID', ogr.OFTInteger))
path_lyr.CreateField(ogr.FieldDefn('POP_NODE', ogr.OFTInteger))
path_lyr.CreateField(ogr.FieldDefn('SHEL_NODE', ogr.OFTInteger))
path_lyr.CreateField(ogr.FieldDefn('POP', ogr.OFTReal))
path_lyr.CreateField(ogr.FieldDefn('CAP', ogr.OFTReal))
path_lyr.CreateField(ogr.FieldDefn('LEN', ogr.OFTReal))
path_lyr.CreateField(ogr.FieldDefn('HAZARD', ogr.OFTReal))

### Start the algorithm
while True :
    print('--------------------')
    ## find the shortest path
    min_cost = shortest_df[(shortest_df['POP_COPY']>0) & (shortest_df['CAP_COPY']>0)]['LEN'].min() # select the population that has the shortest path
    print('cost: ' + str(min_cost))
    index = shortest_df.loc[(shortest_df['POP_COPY']>0) & (shortest_df['CAP_COPY']>0) &
                            (shortest_df['LEN'] == min_cost)].index.values[0] # get row index
    print('index: ' + str(index))
    
    ## get values
    pop = float(shortest_df.iloc[index]['POP_COPY'])
    cap = float(shortest_df.iloc[index]['CAP_COPY'])
    pop_id = shortest_df.iloc[index]['POP_ID']
    print('pop id: ' + str(pop_id))
    shel_id = shortest_df.iloc[index]['SHELTER_ID']
    print('shel_id: ' + str(shel_id))
    pop_node = int(shortest_df.iloc[index]['POP_NODE'])
    shel_node = int(shortest_df.iloc[index]['SHELTER_NODE'])
    length = shortest_df.iloc[index]['LEN']
    hazard = shortest_df.iloc[index]['HAZARD']
    shortest_path = nx.dijkstra_path(G, pop_node, shel_node, weight='LEN')
    
    ## assigning
    if cap >= pop :
        shortest_df.iloc[shortest_df[shortest_df['POP_ID']==pop_id].index.values, pop_copy_index] = 0
        shortest_df.iloc[shortest_df[shortest_df['SHELTER_ID']==shel_id].index.values, cap_copy_index] = cap - pop
        shortest_df.iloc[index, assign_index] = pop
        ## draw routes
        geom = ogr.Geometry(ogr.wkbLineString)
        ## Create multilinestring
        for i in range(0,len(shortest_path)):
            x = float(dict_numToCoor[str(shortest_path[i])].split(',')[0])
            y = float(dict_numToCoor[str(shortest_path[i])].split(',')[1])
            geom.AddPoint(x, y)
        ## input field value
        feat = ogr.Feature(path_defn)
        feat.SetField('POP_ID', int(pop_id))
        feat.SetField('SHEL_ID', int(shel_id))
        feat.SetField('POP_NODE', int(pop_node))
        feat.SetField('SHEL_NODE', int(shel_node))
        feat.SetField('POP', pop)
        feat.SetField('CAP', cap - pop)
        feat.SetField('LEN', length)
        feat.SetField('HAZARD', hazard)
        feat.SetGeometry(geom)
#         print(feat.geometry())
        path_lyr.CreateFeature(feat)
        total_pop = total_pop - pop
        total_cap = total_cap - pop
    else :
        shortest_df.iloc[shortest_df[shortest_df['POP_ID']==pop_id].index.values, pop_copy_index] = pop - cap
        shortest_df.iloc[shortest_df[shortest_df['SHELTER_ID']==shel_id].index.values, cap_copy_index] = 0
        shortest_df.iloc[index, assign_index] = cap
        ## draw routes
        geom = ogr.Geometry(ogr.wkbLineString)
        ## Create multilinestring
        for i in range(0,len(shortest_path)):
            x = float(dict_numToCoor[str(shortest_path[i])].split(',')[0])
            y = float(dict_numToCoor[str(shortest_path[i])].split(',')[1])
            geom.AddPoint(x, y)
        ## input field value
        feat = ogr.Feature(path_defn)
        feat.SetField('POP_ID', int(pop_id))
        feat.SetField('SHEL_ID', int(shel_id))
        feat.SetField('POP_NODE', int(pop_node))
        feat.SetField('SHEL_NODE', int(shel_node))
        feat.SetField('POP', cap)
        feat.SetField('CAP', 0)
        feat.SetField('LEN', length)
        feat.SetField('HAZARD', hazard)
        feat.SetGeometry(geom)
#         print(feat.geometry())
        path_lyr.CreateFeature(feat)
        total_pop = total_pop - cap
        total_cap = total_cap - cap
    print('total pop: ' + str(total_pop))
    print('total cap: ' + str(total_cap))
    if shortest_df['POP_COPY'].sum() <= 0 :
        print('assigning is finish!')
        break
    if shortest_df['CAP_COPY'].sum() <= 0 :
        print('capacity issue!')
        break
        
## close path
path_ds.Destroy()
## save the results
shortest_df.to_json('.json')
shortest_df.to_csv('.csv')

cd = asd.loc[shortest_df["ASSIGN"] > 0]
cd.to_json('.json')
cd.to_csv('.csv')
