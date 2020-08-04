from matplotlib import pyplot as plt
import matplotlib as mplv
import numpy as np
import pandas as pd
import xarray as xr
import zarr
import gcsfs
# import intake

np.seterr(divide='ignore', invalid='ignore')  # Divide by Nan warning, well it doesn't work

plt.rcParams['figure.figsize'] = 12, 6
# xr.set_options(display_style='html')
# Need to set dtype or we run out of memory
df = pd.read_csv('https://storage.googleapis.com/cmip6/cmip6-zarr-consolidated-stores.csv', dtype={"version": "string"})

# df_CMIP = df[df['activity_id'] == "CMIP"]   # Pick CMIP experiments , COMMENT THIS, Scenario MIP Is the one
df_CMIP = df
df_ssp245 = df_CMIP[df_CMIP['experiment_id'].str.contains("ssp2")]      # 1pctCO2
df_tos = df_ssp245[df_ssp245['variable_id'] == "tos"]    # Keep Ocean Temperature
df_tos_monthly = df_tos[df_tos['table_id'] == "Omon"]    # Monthly outputs
df_tos_monthly_gn = df_tos_monthly[df_tos_monthly['grid_label'] == "gn"]    # Primary grid , some have faces

df_tos_unique = df_tos_monthly_gn.drop_duplicates(subset='source_id')  # Just keep 1 realization

# this only needs to be created once
gcs = gcsfs.GCSFileSystem(token='anon') # get the path to a specific zarr store (the first one from the dataframe above)

# for i in range(len(df_sos_unique.source_id.tolist())):

nyear = '2050'
iexperiment = 1
zstore0 = df_tos_unique.zstore.values[iexperiment]

# create a mutable-mapping-style interface to the store
mapper0 = gcs.get_mapper(zstore0)
ds0 = xr.open_zarr(mapper0, consolidated=True, decode_times=True)
ds0 = xr.decode_cf(ds0)

#### The following block does standardization of coord names
lat_name = 'lat'
if 'latitude' in ds0.coords: lat_name = 'latitude'
lon_name = 'lon'
if 'longitude' in ds0.coords: lon_name = 'longitude'
lon0 = eval('ds0.'+lon_name)
lat0 = eval('ds0.'+lat_name)
####

# data0_mean = ds0.tos.sel(time=slice(nyear+'-01', nyear+'-01')).squeeze().mean(dim='time')
data0_mean = ds0.tos.sel(time=slice(nyear+'-01', nyear+'-01')).squeeze()

# now lets open another set and interpolate
# iexperiment = 2

iexperiment = 2
zstore = df_tos_unique.zstore.values[iexperiment]
# create a mutable-mapping-style interface to the store
mapper = gcs.get_mapper(zstore)
ds = xr.open_zarr(mapper, consolidated=True, decode_times=True)
ds = xr.decode_cf(ds)

# ds_interp = ds.interp_like(ds0)
# ds_interp = ds

lat_name = 'lat'
if 'latitude' in ds.coords: lat_name = 'latitude'
lon_name = 'lon'
if 'longitude' in ds.coords: lon_name = 'longitude'
lon = eval('ds.'+lon_name)
lat = eval('ds.'+lat_name)


####
data_mean = ds.tos.sel(time=slice(nyear+'-01', nyear+'-01')).squeeze(drop=True)
#
data_interp_mean = data_mean.interp_like(data0_mean)
# data_interp_mean = ds_interp.tos.sel(time=slice(nyear+'-01', nyear+'-01')).squeeze(drop=True)
#
# data_std = ds.sos.sel(time=slice(nyear, nyear)).squeeze().std(dim='time')
#
#
# # The following does plotting
fig1, ax = plt.subplots(3, 1)
clmap = ax[0].pcolormesh(lon, lat, data_mean, vmin=0, vmax=30)
clbar = plt.colorbar(clmap, ax=ax[0], pad=0.02)
ax[0].axis('tight')
ax[0].set_title('year = ' + nyear + '\n' + ds.title)
clbar.ax.set_ylabel('Mean SSS', rotation=270, fontsize=12)
clbar.ax.get_yaxis().labelpad = 13  # Does the spacing between number and clbar
#
clmap = ax[1].pcolormesh(lon0, lat0, data0_mean, vmin=0, vmax=30)
clbar = plt.colorbar(clmap, ax=ax[1], pad=0.02)
ax[1].axis('tight')
# ax[1].set_title(ds0.title)
clbar.ax.set_ylabel('Reference frame from ' + '\n' + ds0.title + '\n' + ' SSS', rotation=270, fontsize=12)
clbar.ax.get_yaxis().labelpad = 45  # Does the spacing between number and clbar
#
clmap = ax[2].pcolormesh(lon, lat, data_interp_mean, vmin=0, vmax=30)
clbar = plt.colorbar(clmap, ax=ax[2], pad=0.02)
ax[2].axis('tight')
clbar.ax.set_ylabel('Interp Mean SSS', rotation=270, fontsize=12)
clbar.ax.get_yaxis().labelpad = 13  # Does the spacing between number and clbar
# #
# # plt.show()
