from matplotlib import pyplot as plt
import matplotlib as mplv
import numpy as np
import pandas as pd
import xarray as xr
import zarr
import gcsfs

np.seterr(divide='ignore', invalid='ignore')  # Divide by Nan warning, well it doesn't work

plt.rcParams['figure.figsize'] = 12, 6
# xr.set_options(display_style='html')
# Need to set dtype or we run out of memory
df = pd.read_csv('https://storage.googleapis.com/cmip6/cmip6-zarr-consolidated-stores.csv', dtype={"version": "string"})
# df_ta = df.query("activity_id=='CMIP' & table_id == 'Amon' & variable_id == 'tas' & experiment_id == 'historical'")
# df_ta = df.query("activity_id=='CMIP'  & variable_id == 'ts' & experiment_id == 'historical'")
# df_ta = df.query("activity_id == 'CMIP' & table_id == 'Oyr' & experiment_id == 'historical'")
df_CMIP = df.query("activity_id == 'CMIP' & experiment_id == 'historical'")
# I am not sure each model is unique but try getting all sea surface salinities
df_sos = df_CMIP.query("variable_id == 'sos' & member_id == 'r1i1p1f1'")  # looking for Sea surface salinity
# df_sos_unique = df_sos.drop_duplicates(subset='source_id')
df_sos_unique = df_sos
# this only needs to be created once
gcs = gcsfs.GCSFileSystem(token='anon')
# get the path to a specific zarr store (the first one from the dataframe above)

# data = ds.sos.sel(time=1444656).__array__()
# lat = ds.latitude
# for i in range(len(df_sos_unique.source_id.tolist())):


zstore = df_sos_unique.zstore.values[-1]
# zstore = df_sos_unique.zstore.values[1]


# create a mutable-mapping-style interface to the store
mapper = gcs.get_mapper(zstore)
# open it using xarray and zarr
ds = xr.open_zarr(mapper, consolidated=True, decode_times=True)

### THIS DATA SET IS UNRELIABLE , THE TIME IS ALL OVER THE PLACE !!!!
# ds.sos.sel(time=slice('2012')).squeeze().plot(vmin=28, vmax=35)

nyear = '2002'

lon = ds.longitude
# lon = ds.lon
lat = ds.latitude
# lat = ds.lat
data_mean = ds.sos.sel(time=slice(nyear, nyear)).squeeze().mean(dim='time')
data_std = ds.sos.sel(time=slice(nyear, nyear)).squeeze().std(dim='time')

fig1, ax = plt.subplots(2, 1)
clmap = ax[0].pcolormesh(lon, lat, data_mean, vmin=28, vmax=35.5)
clbar = plt.colorbar(clmap, ax=ax[0], pad=0.02)
ax[0].axis('tight')
ax[0].set_title('year = ' + nyear + '\n' + ds.title)
clbar.ax.set_ylabel('Mean SSS', rotation=270, fontsize=12)
clbar.ax.get_yaxis().labelpad = 13  # Does the spacing between number and clbar

clmap = ax[1].pcolormesh(lon, lat, data_std, vmin=-1, vmax=1)
clbar = plt.colorbar(clmap, ax=ax[1], pad=0.02)
ax[1].axis('tight')
clbar.ax.set_ylabel('STD SSS', rotation=270, fontsize=12)

plt.show()
