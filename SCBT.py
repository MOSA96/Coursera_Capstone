#!/usr/bin/env python
# coding: utf-8

# # <center>  Segmenting and Clustering Neighborhoods in Toronto </center>

# In[2]:


import numpy as np
import pandas as pd 
import json
from geopy.geocoders import Nominatim 
import requests
from pandas.io.json import json_normalize
import matplotlib.cm as cm
import matplotlib.colors as colors
from sklearn.cluster import KMeans
import folium 


# #  <center> First part </center>

# In[38]:


from bs4 import BeautifulSoup
website_url = requests.get("https://en.wikipedia.org/wiki/List_of_postal_codes_of_Canada:_M").text


# In[39]:


soup = BeautifulSoup(website_url, "xml")
print(soup.prettify())


# In[40]:


table = soup.find('table')


# In[54]:


#column_names = ['Postal Code','Borough','Neighborhood']
df = pd.DataFrame(columns = ['Postal Code','Borough','Neighborhood'])


# In[55]:


for tr_cell in table.find_all('tr'):
    data=[]
    for td_cell in tr_cell.find_all('td'):
        data.append(td_cell.text.strip())
    if len(data)==3:
        df.loc[len(df)] = data


# In[56]:


df.head()


# In[57]:


df = df[df.Borough != 'Not assigned']


# In[58]:


df.head()


# In[59]:


df2=df.groupby('Postal Code')['Neighborhood'].apply(lambda x: "%s" % ', '.join(x))
df2=df2.reset_index(drop=False)
df2.rename(columns={'Neighborhood':'Neighborhoods'},inplace=True)


# In[60]:


df2.head()


# In[61]:


df3 = pd.merge(df, df2, on = "Postal Code")


# In[62]:


df3.drop(["Neighborhood"], axis=1, inplace = True)


# In[63]:


df3.rename(columns={"Neighborhoods": "Neighborhood"}, inplace=True)


# In[64]:


df3.head()


# In[65]:


df3.shape


# # <center> Second Part </center>

# In[72]:


geo_df=pd.read_csv('http://cocl.us/Geospatial_data')


# In[73]:


geo_df.head()


# In[79]:


geo_combine = pd.merge(geo_df, df3, on="Postal Code")


# In[80]:


geo_combine.head()


# In[82]:


geo_combine = geo_combine[["Postal Code", "Borough", "Neighborhood","Latitude", "Longitude"]]


# In[83]:


geo_combine.head()


# In[86]:


geo_combine.shape


# # <center> Third Part </center>

# In[87]:


toronto = geo_combine[geo_combine["Borough"].str.contains("Toronto")]


# In[88]:


toronto.head()


# In[89]:


toronto.shape


# In[90]:


CLIENT_ID = 'DFPZ4OFM3OLICN3VS4B1CSOAV2EWN2MSA5XMN4J2U5CPHRXP' # your Foursquare ID
CLIENT_SECRET = '4WTK4TTFXMWT5EBN2P1EMOQWKIMCYKHXWPWFI1UCTATL1AQW' # your Foursquare Secret
VERSION = '202080706'


# In[91]:


def getNearbyVenues(names, latitudes, longitudes):
    radius=500
    LIMIT=100
    venues_list=[]
    for name, lat, lng in zip(names, latitudes, longitudes):
        print(name)
            
        # create the API request URL
        url = 'https://api.foursquare.com/v2/venues/explore?&client_id={}&client_secret={}&v={}&ll={},{}&radius={}&limit={}'.format(
            CLIENT_ID, 
            CLIENT_SECRET, 
            VERSION, 
            lat, 
            lng, 
            radius, 
            LIMIT)
            
        # make the GET request
        results = requests.get(url).json()["response"]['groups'][0]['items']
        
        # return only relevant information for each nearby venue
        venues_list.append([(
            name, 
            lat, 
            lng, 
            v['venue']['name'], 
            v['venue']['location']['lat'], 
            v['venue']['location']['lng'],  
            v['venue']['categories'][0]['name']) for v in results])

    nearby_venues = pd.DataFrame([item for venue_list in venues_list for item in venue_list])
    nearby_venues.columns = ['Neighborhood', 
                  'Neighborhood Latitude', 
                  'Neighborhood Longitude', 
                  'Venue', 
                  'Venue Latitude', 
                  'Venue Longitude', 
                  'Venue Category']
    
    return(nearby_venues)


# In[94]:


toronto_venues = getNearbyVenues(names=toronto['Neighborhood'],
                                   latitudes=toronto['Latitude'],
                                   longitudes=toronto['Longitude']
                                  )


# In[96]:


toronto_venues.head()


# In[97]:


toronto_venues.groupby('Neighborhood').count()


# In[98]:


toronto_onehot = pd.get_dummies(toronto_venues[['Venue Category']], prefix="", prefix_sep="")
toronto_onehot.drop(['Neighborhood'],axis=1,inplace=True) 
toronto_onehot.insert(loc=0, column='Neighborhood', value=toronto_venues['Neighborhood'] )
toronto_onehot.shape


# In[99]:


toronto_grouped = toronto_onehot.groupby('Neighborhood').mean().reset_index()
toronto_grouped.head()


# In[100]:


def return_most_common_venues(row, num_top_venues):
    row_categories = row.iloc[1:]
    row_categories_sorted = row_categories.sort_values(ascending=False)
    
    return row_categories_sorted.index.values[0:num_top_venues]


# In[102]:


num_top_venues = 10
indicators = ['st', 'nd', 'rd']


columns = ['Neighborhood']
for ind in np.arange(num_top_venues):
    try:
        columns.append('{}{} Most Common Venue'.format(ind+1, indicators[ind]))
    except:
        columns.append('{}th Most Common Venue'.format(ind+1))


neighborhoods_venues_sorted = pd.DataFrame(columns=columns)
neighborhoods_venues_sorted['Neighborhood'] = toronto_grouped['Neighborhood']

for ind in np.arange(toronto_grouped.shape[0]):
    neighborhoods_venues_sorted.iloc[ind, 1:] = return_most_common_venues(toronto_grouped.iloc[ind, :], num_top_venues)


# In[103]:


neighborhoods_venues_sorted.head()


# In[104]:


# k-means clustering
kclusters = 5

toronto_grouped_clustering = toronto_grouped.drop('Neighborhood', 1)


kmeans = KMeans(n_clusters=kclusters, random_state=0).fit(toronto_grouped_clustering)

kmeans.labels_[0:10]


# In[115]:


toronto_merged = toronto
toronto_merged = toronto_merged.join(neighborhoods_venues_sorted.set_index('Neighborhood'), on='Neighborhood')


# In[116]:


toronto_merged.head()


# In[117]:


neighborhoods_venues_sorted.head()    


# In[119]:


address = 'Toronto, CA'

geolocator = Nominatim(user_agent="ny_explorer")
location = geolocator.geocode(address)
latitude = location.latitude
longitude = location.longitude
print('The geograpical coordinate of Manhattan are {}, {}.'.format(latitude, longitude))


# In[120]:


map_clusters = folium.Map(location=[latitude, longitude], zoom_start=11)

# color 
x = np.arange(kclusters)
ys = [i + x + (i*x)**2 for i in range(kclusters)]
colors_array = cm.rainbow(np.linspace(0, 1, len(ys)))
rainbow = [colors.rgb2hex(i) for i in colors_array]

#markers 
markers_colors = []
for lat, lon, poi, cluster in zip(toronto_merged['Latitude'], toronto_merged['Longitude'], toronto_merged['Neighborhood'], toronto_merged['Cluster Labels']):
    label = folium.Popup(str(poi) + ' Cluster ' + str(cluster), parse_html=True)
    folium.CircleMarker(
        [lat, lon],
        radius=5,
        popup=label,
        color=rainbow[cluster-1],
        fill=True,
        fill_color=rainbow[cluster-1],
        fill_opacity=0.7).add_to(map_clusters)
       
map_clusters


# In[ ]:




