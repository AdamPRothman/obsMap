#!/usr/bin/env python
# coding: utf-8

# In[ ]:





# CNFAIC Observation Map
# Goal:
# Make a map of recent (<7 days) observations.  
#     
# To Do:
# - Make popups nice
# - Add wx with different markers
# - Create website with legend around map
# - Layer options and menu clean-up
# 
# 
# Ideas:
# - Custom date range
# - Professional only mode(?)
# 
# Low Priority:
# - Fix encoding in notebook
# - Fix flag count. There will be issues if other tables or length of avalanche table has additional rows. Maybe can rework this based on table content
#     rather than the number of total table rows in the page
# 

# In[1]:


#Load libraries
import base64
import pandas as pd
pd.options.mode.chained_assignment = None  # default='warn'
import numpy as np
import folium
from folium import IFrame
import folium.plugins as plugins
from urllib.request import urlopen
from bs4 import BeautifulSoup
import re
import datetime


# In[17]:


#Observation dataframe
try:
    pd.read_pickle('./obsArchive.pkl')
except:
    
    Obs = pd.DataFrame(columns = ('Location', 'Date', 'Observer','Lat','Lon'))

#read observation archive

obsArchive = pd.read_pickle('./obsArchive.pkl')


# In[3]:



def getObs(url):
    #Open url and convert to soup
    html = urlopen(url).read()
    soup = BeautifulSoup(html)
    with open('./Observations/'+ url[36:-1], 'a') as file: file.write(str(soup))
    
    #Pull location
    location = str(soup.find('title'))
    #location = location.replace("[\\u2018\\u2019]", "'") #Replace curly single quote with straight
    location = location[7:location.find('|') - 1]
    
    #Pull observer info, first check for anonymous report
    if str(soup.select_one(
        'div[ class *= cnfaic_obs-table-browse-observations-byline]')) \
        == '<div class="cnfaic_obs-table-browse-observations-byline">Anonymous</div>':
        observer = 'Anonymous'
    else:
        observer = soup.select_one("span[class *= cnfaic_obs-table-browse-observations-byline]").text
        observer = observer[:-1]
        
    #Pull date
    date = soup.select('div[ class *= "top_meta"]')
    date = date[1].text
    formattedDate = formatTime(date)
    
    #Pull coordinates
    if len(soup.find_all("a", href=lambda href: href and "google" in href)) > 0:
        links = soup.find_all("a", href=lambda href: href and "google" in href)
        coords = str(links[0])
        coords = coords[coords.find('q='):coords.find("'>")]
        lat = float(coords[coords.find('=') + 1 : coords.find(',') - 1])
        lon = float(coords[coords.find(",") + 1 : coords.find('target') - 2])
    else:
        lat = float('NaN')
        lon = float('NaN')
        
    #Red Flags
    if soup.find_all('tr') != []:
        table = soup.find_all('tr')
        rows = soup.find_all('tr')
        flags = []
        if len(rows) == 4: #Check for avalanche table, if avy table is there length is 7
            for row in rows:
                cols = row.find_all('td')
                cols = [ele.text.strip() for ele in cols]
                flags.append([ele for ele in cols if ele]) 
            avyReport = False
        else: #if avy table is above red flag table then this will work, assuming there isn't a table below it
            rows = rows[-3:]
            for row in rows:
                cols = row.find_all('td')
                cols = [ele.text.strip() for ele in cols]
                flags.append([ele for ele in cols if ele]) 
            avyReport = True
                
        recentAvy = flags[0][1] == 'Yes'
        collapsing = flags[1][1] == 'Yes'
        cracking = flags[2][1] == 'Yes'
    else:
        recentAvy = False
        collapsing = False
        cracking = False
        avyReport = False
    
    flagCount = 0
    if recentAvy == True:
        flagCount += 1
    if collapsing == True:
        flagCount += 1
    if cracking == True:
        flagCount += 1
        
    
    #Create dataframe from data
    d = {'Date':[formattedDate],'Location':[location], 'Observer':[observer],'Lat':[lat], 
         'Lon': [lon], 'Avy Report':[avyReport], 'Recent Avy':[recentAvy], 'Collapsing' : [collapsing], 
         'Cracking' : [cracking], 'flagCount' : flagCount, 'url' : [url]}
    oneObs = pd.DataFrame(data = d)
    
    #Pull red flags

    return(oneObs)


# In[ ]:





# In[4]:


def getUrls():
    url = 'https://www.cnfaic.org/view-observations/'
    html = urlopen(url).read()
    soup = BeautifulSoup(html)
    table = soup.find('table')
    links = table.find_all('a')
    urls = list()
    gallery = 'gallery'
    i = 0
    for link in range(len(links)):
        if gallery in str(links[link]):
            i = i
        else:
            url = str(links[link])
            url = url[ 9 : url.find('>') - 1]
            if (obsArchive['url'] == url).any():
                i = i
            else:
                urls.append(url)
                i += 1
    return(urls)

    


# In[5]:


def getNewObs():
    newObs = pd.DataFrame()
    urls = getUrls()
    for i in range(len(urls)):  #Changed this
        newObs = newObs.append(getObs(urls[i]))
    
    newObs.reset_index(inplace = True, drop = True)
    newObs['url'] = urls
    return(newObs)    


# In[6]:


def addNewObs(obsArchive):
    newObs = getNewObs()

    for i in range(len(newObs)):
        obsArchive = obsArchive.append(newObs.iloc[i])       
        #Save the soup to the observations folder
        #with open('./Observations/'+ url[36:-1], 'a') as file: file.write(str(soup))
            
    obsArchive = obsArchive.sort_values('Date', ascending = False)    
    obsArchive.reset_index(inplace = True, drop = True)

    obsArchive.to_pickle('./obsArchive.pkl')
    return(obsArchive)
        


# In[7]:


def formatTime(dateString):

    i = 0
    calendar = {'Jan':'01', 'Feb':'02', 'Mar':'03', 'Apr':'04', 'May':'05', 'Jun':'06', 'Jul':'07',
               'Aug':'08', 'Sep':'09', 'Oct':'10', 'Nov':'11', 'Dec':'12'}
    month = calendar[dateString[0:3]]

    day = dateString[dateString.find(',')-2:dateString.find(',')]
    if day[0] == ' ':
        day = '0' + day[1]

    year = dateString[dateString.find(',')+2:dateString.find(',')+6]
    year
    if dateString[-1] == 'm':
        time = dateString[-7:]
        ap = ''
        if time[0] == ' ':
            time = '0' + time[1:]
    else:
        time = dateString[-5:]
        if time[0] == ' ':
            time = '0' + time[1:]
        if int(time[0:2]) > 7: 
            ap = 'am'
        else:
            ap = 'pm'
            

    dateString = str(year) + '-' + str(month) + '-' + str(day) + ' ' + time + ap
    try:
        datetime.datetime.strptime(dateString, '%Y-%m-%d %H:%M%p')
    except:
        date = datetime.datetime.strptime(dateString, '%Y-%m-%d %H:%M')
    else:
        date = datetime.datetime.strptime(dateString, '%Y-%m-%d %H:%M%p')
    return(date)


# In[8]:


obsArchive = addNewObs(obsArchive)
obsArchive


# In[ ]:





# In[ ]:





# In[9]:


#Filter obs archive into 3 groups based on age of obs

today = datetime.datetime.today()
oneDay = datetime.timedelta(days = 2)
threeDays = datetime.timedelta(days = 4)
oneWeek = datetime.timedelta(days = 8)
i = 0


for i in range(len(obsArchive)):
    if obsArchive.iloc[i][0].replace(hour = 0, minute = 0, second = 0) + oneDay > today:
        obsArchive['ageGroup'][i] = 'yesterday'
    elif obsArchive.iloc[i][0].replace(hour = 0, minute = 0, second = 0) + threeDays > today:
        obsArchive['ageGroup'][i] = '3 day'
    elif obsArchive.iloc[i][0].replace(hour = 0, minute = 0, second = 0) + oneWeek > today:
        obsArchive['ageGroup'][i] = 'week'
    else:
        obsArchive['ageGroup'][i] = 'old'


obsArchive



# In[10]:


dfYes = obsArchive[obsArchive['ageGroup'].isin(['yesterday'])]
df3day = obsArchive[obsArchive['ageGroup'].isin(['3 day'])]
dfWeek = obsArchive[obsArchive['ageGroup'].isin(['week'])]


# In[16]:


# Load USGS
url_base = 'http://server.arcgisonline.com/ArcGIS/rest/services/'
service = 'NatGeo_World_Map/MapServer/tile/{z}/{y}/{x}'
tileset = url_base + service

# Create the map
m = folium.Map(location = [60.79443,-149.199667], zoom_start = 11, tiles = tileset,
               attr='USGS Style')


# Add markers to map
"""for i in range(len(obsArchive)):
    if str(obsArchive.iloc[i][3]) != 'nan':
        folium.Marker([obsArchive.iloc[i][3],obsArchive.iloc[i][4]], popup = 
                      obsArchive.iloc[i][1] + ' ' +
                      '<a href="%s" target="_blank">Link</a>' % obsArchive.iloc[i][8]).add_to(m)
    """


fgObs = folium.FeatureGroup(name = 'Observations')
m.add_child(fgObs)
gYes = folium.plugins.FeatureGroupSubGroup(fgObs, 'Yesterday')
g3day = folium.plugins.FeatureGroupSubGroup(fgObs, '3 Days')
gWeek = folium.plugins.FeatureGroupSubGroup(fgObs, 'One Week')
subGroups = [gYes, g3day, gWeek]


frames = [dfYes, df3day, dfWeek]
colors = ['red', 'green', 'blue']
resolution, width, height = (72, 40, 40)

#iterate through the three time frames:
for i in range(len(frames)):
    m.add_child(subGroups[i])
    
    #iterate through the obs:
    for j in range(len(frames[i])):
        if str(frames[i]['Lat'].iloc[j]) != 'nan':  #only handle observations with coordinates
            filename = 'flag (' + str(int(frames[i]['flagCount'].iloc[j])) + ').jpg' #load correct flag image
            encodedFlag = base64.b64encode(open(filename, 'rb').read())
            flagImage='<img src="data:image/jpeg;base64,{}">'.format 
            
            if frames[i]['Avy Report'].iloc[j] == True:
                filename = 'avyIcon.png'
                encodedAvy = base64.b64encode(open(filename, 'rb').read())
                avyImage = '<img src="data:image/png;base64,{}">'.format
            else:
                avyImage = ''
            
            #create html for IFrame
            if avyImage == '':
                html = ('<b style="font-family:Helvetica,Arial,sans-serif; font-size: 16px;"> ' 
                    + '<a href="{}" target="_blank">{}</a>'.format(frames[i]['url'].iloc[j], frames[i]['Location'].iloc[j])
                    + '</b> <br /> <body style="font-family:Helvetica,Arial,sans-serif; font-size: 14px;">'
                    + frames[i].iloc[j][2] + '<br />'
                    + frames[i].iloc[j][0].strftime("%m/%d/%Y, %H:%M %p") + '</body> <br>'
                    + flagImage(encodedFlag.decode('UTF-8')))
            else:
                html = ('<b style="font-family:Helvetica,Arial,sans-serif; font-size: 16px;"> ' 
                    + '<a href="{}" target="_blank">{}</a>'.format(frames[i].iloc[j][9], frames[i].iloc[j][1])
                    + '</b> <br /> <body style="font-family:Helvetica,Arial,sans-serif; font-size: 14px;">'
                    + frames[i]['Observer'].iloc[j] + '<br />'
                    + frames[i]['Date'].iloc[j].strftime("%m/%d/%Y, %H:%M %p") + '</body> <br>'
                    + flagImage(encodedFlag.decode('UTF-8'))
                    + avyImage(encodedAvy.decode('UTF-8')))
            #Create IFrame
            iframe = IFrame(html, width = 2000)
            popup = folium.Popup(iframe, min_width = 200, max_width = 2000)
            
            #add marker to subgroup
            subGroups[i].add_child(
                folium.Marker([frames[i].iloc[j][3],
                frames[i].iloc[j][4]], 
                popup = popup,
                icon = folium.Icon(color = colors[i])))

folium.LayerControl().add_to(m)
m

