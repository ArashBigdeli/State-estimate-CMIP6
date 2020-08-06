from matplotlib import pyplot as plt
import matplotlib as mplv
import os
import numpy as np
import pandas as pd
import xarray as xr
import zarr
import gcsfs
import scipy
from scipy import interpolate
from scipy.spatial import Delaunay
# import intake

np.seterr(divide='ignore', invalid='ignore')  # Divide by Nan warning, well it doesn't work

plt.rcParams['figure.figsize'] = 12, 6
# xr.set_options(display_style='html')
# Need to set dtype or we run out of memory

variable_interest = "tos"
scenario_intrest = "ssp245"
df = pd.read_csv('https://storage.googleapis.com/cmip6/cmip6-zarr-consolidated-stores.csv', dtype={"version": "string"})

# df_CMIP = df[df['activity_id'] == "CMIP"]   # Pick CMIP experiments , COMMENT THIS, Scenario MIP Is the one
df_CMIP = df
df_scenario = df_CMIP[df_CMIP['experiment_id'].str.contains(scenario_intrest)]      # 1pctCO2
df_var = df_scenario[df_scenario['variable_id'] == variable_interest]    # Keep Ocean Temperature
df_var_monthly = df_var[df_var['table_id'] == "Omon"]    # Monthly outputs
df_var_monthly_gn = df_var_monthly[df_var_monthly['grid_label'] == "gn"]    # Primary grid , some have faces

df_var_unique = df_var_monthly_gn.drop_duplicates(subset='source_id')  # Just keep 1 realization

# this only needs to be created once
gcs = gcsfs.GCSFileSystem(token='anon') # get the path to a specific zarr store (the first one from the dataframe above)

nyear = '2050'
iexperiment0 = 1 # This is BCC-CSM2-MR , a good coarse resolution to bring everything on
zstore0 = df_var_unique.zstore.values[iexperiment]

# create a mutable-mapping-style interface to the store
mapper0 = gcs.get_mapper(zstore0)
ds0 = xr.open_zarr(mapper0, consolidated=True, decode_times=True)
ds0 = xr.decode_cf(ds0)

#### The following block does standardization of coord names
if ('longitude' in ds0.dims) and ('latitude' in ds0.dims):
    ds0 = ds0.rename({'longitude':  'lon', 'latitude': 'lat'})
lon0 = ds0.lon
lat0 = ds0.lat
lon0_values = lon0.values
lat0_values = lat0.values
lon0_grid, lat0_grid = np.meshgrid(lon0_values, lat0_values)

data0 = eval('ds0.' + variable_interest).sel(time=slice(nyear + '-01', nyear + '-01')).squeeze()
data0_values = data0.values

# data_ensembles = data0_mean # stop working with xarray here , no point in complexity of this until i learn more
data_ensembles = data0_values
#

# # now lets open another set and interpolate
ignore_list = [0, 24, 33]  # These have faces, i can't handle those atm, ran out of mem
ignore_list.append(9)  #This one does not have 2050 runs till 2020
ignore_list.append(19)  # This one runs until end of 2039
ignore_list.append(iexperiment0)    #Double counting

cmip_list = [ind for ind in range(len(df_var_unique.source_id.tolist())) if ind not in ignore_list]

for iexperiment in cmip_list:
    print('Started #' + str(iexperiment) + ' From ' + str(len(cmip_list)))
    zstore = df_var_unique.zstore.values[iexperiment]
    mapper = gcs.get_mapper(zstore)
    ds = xr.open_zarr(mapper, consolidated=True, decode_times=True)
    ds = xr.decode_cf(ds)

    lon_name = 'lon'
    lat_name = 'lat'
    try:
        lon = eval('ds.' + lon_name)
        lat = eval('ds.' + lat_name)
    except:
        if 'longitude' in ds.coords:
            lon_name = 'longitude'
            lat_name = 'latitude'
        if 'nav_lon' in ds.coords:
            lon_name = 'nav_lon'
            lat_name = 'nav_lat'

        lon = eval('ds.' + lon_name)
        lat = eval('ds.' + lat_name)

    lon_values = lon.values
    lat_values = lat.values

    data = eval('ds.' + variable_interest).sel(time=slice(nyear+'-01', nyear+'-01')).squeeze()
    # mydata = xr.DataArray(data.values, [("lat" = data.latitude.values), ("lon" = data.longitude.values)])
    data_values = data.values


    # data_interp_mean = data_mean.interp(j=lat0, i=lon0) #  this gives the weird + numbers
    # data_interp_mean = data_mean.interp(j=lat0, i=lon0) # this breaks on self interpolation of #1
    # data_interp_mean = data_mean.interp(lat=lat0, lon=lon0) # works on self interploation of #1

    # data_interp = data.interp(lat=lat0, lon=lon0,method= 'linear',assume_sorted='False,') # works on self interploation of #1
    # data_interp = data.interp(lat=lat0, lon=lon0) # works on self interploation of #1

    # data_interp_values = data_interp.values

    ######## Too SLOW
    # f = interpolate.interp2d(lon_values, lat_values, data_values, kind='linear')
    # data_interp_values = f(lon_values, lat0_values)
    ######

    ##### Too garbage
    # lon_values_1d = lon_values.flatten()
    # lat_values_1d = lat_values.flatten()
    # data_values_1d = data_values.flatten()
    # data_interp_values = interpolate.griddata((lon_values_1d, lat_values_1d), data_values_1d, (lon0_values, lat0_values), method='nearest')
    ########

    ### For consistency I have to bring Vector of lats and cords to
    ### scipy.interpolate.LinearNDInterpolator
    if lon_values.ndim == 1:
        lon_values, lat_values = np.meshgrid(lon_values, lat_values)
    ###
    lon_values_1d = lon_values.flatten()
    lon_values_1d[lon_values_1d < 0] = lon_values_1d[lon_values_1d < 0] + 360
    lat_values_1d = lat_values.flatten()
    data_values_1d = data_values.flatten()
    points = list(zip(lon_values_1d, lat_values_1d))
    interp_surface = interpolate.LinearNDInterpolator(points, data_values_1d)
    data_interp_values = interp_surface(lon0_grid, lat0_grid)
    # data_interp_values = scipy.interpolate.interpn((lat, lon), data_values, (lat0, lon0), method='nearest')

    # xr.concat([data0, data_interp], 'ensembles') # stopped using xarray
    data_ensembles = np.dstack((data_ensembles, data_interp_values))
    print('Finished #' + str(iexperiment) + ' From ' + str(len(cmip_list)))
    fig, ax = plt.subplots(3)
    # data.plot(ax=ax[0], vmin=5, vmax=30)
    ax[0].pcolormesh(data, cmap='RdBu_r', vmin=5, vmax=30)
    ax[0].set_title('Data : ' + str(ds.source_id))

    ax[1].pcolormesh(lon0_values, lat0_values, data0_values, vmin=5, vmax=30, cmap='RdBu_r')
    ax[1].set_title('Target grid : ' + str(ds0.source_id))

    pcolor_h = ax[2].pcolormesh(lon0_values, lat0_values, data_interp_values, vmin=5, vmax=30, cmap='RdBu_r')
    ax[2].set_title('Interpolation')
    fig.tight_layout()

    fig.subplots_adjust(right=0.8)
    cbar_ax = fig.add_axes([0.85, 0.15, 0.01, 0.7])
    fig.colorbar(pcolor_h, cax=cbar_ax)
    cbar_ax.set_ylabel('SST (C)    ' + 'for  Jan ' + str(nyear), rotation=270, fontsize=12, labelpad=13)

    output_name = 'interp_figs/' + str(ds.source_id) + '.png'
    fig.savefig(output_name)
    plt.close(fig)

data_mean = np.nanmean(data_ensembles,axis=2)
data_std = np.nanstd(data_ensembles,axis=2)


fig, ax = plt.subplots()
pcolor_h = ax.pcolormesh(data_mean, cmap='RdBu_r', vmin=5, vmax=30)
ax.set_title('Mean "' + variable_interest + '" for CMIP6 scenario "' + scenario_intrest + '" On  Jan ' + str(nyear))
cbar_ax = fig.colorbar(pcolor_h)
fig.tight_layout()
cbar_ax.ax.set_ylabel('SST (C)', rotation=270, fontsize=12, labelpad=13)
output_name = 'stat_figs/Mean_SST.png'
fig.savefig(output_name)
plt.close(fig)

fig, ax = plt.subplots()
pcolor_h = ax.pcolormesh(data_std, cmap='RdBu_r', vmin=0, vmax=2)
ax.set_title('STD "' + variable_interest + '" for CMIP6 scenario "' + scenario_intrest + '" On  Jan ' + str(nyear))
cbar_ax = fig.colorbar(pcolor_h)
fig.tight_layout()
cbar_ax.ax.set_ylabel('SST (C)', rotation=270, fontsize=12, labelpad=13)
output_name = 'stat_figs/STD_SST.png'
fig.savefig(output_name)
plt.close(fig)

# fig = plt.figure()
# fig.add_subplot(311)
# data.plot()
# fig.add_subplot(312)
# data0.plot()
# fig.add_subplot(313)
# data_interp.plot()
#



# # data_std = ds.sos.sel(time=slice(nyear, nyear)).squeeze().std(dim='time')
# #
# #
# # The following does plotting
# lat = ds.latitude
# lon = ds.longitude
# fig1, ax = plt.subplots(3, 1)
# clmap = ax[0].pcolormesh(lon, lat, data_mean, vmin=0, vmax=30)
# clbar = plt.colorbar(clmap, ax=ax[0], pad=0.02)
# ax[0].axis('tight')
# ax[0].set_title('year = ' + nyear + '\n' + ds.title)
# clbar.ax.set_ylabel('Mean SSS', rotation=270, fontsize=12)
# clbar.ax.get_yaxis().labelpad = 13  # Does the spacing between number and clbar
# #
# clmap = ax[1].pcolormesh(lon0, lat0, data0_mean, vmin=0, vmax=30)
# clbar = plt.colorbar(clmap, ax=ax[1], pad=0.02)
# ax[1].axis('tight')
# # ax[1].set_title(ds0.title)
# clbar.ax.set_ylabel('Reference frame from ' + '\n' + ds0.title + '\n' + ' SSS', rotation=270, fontsize=12)
# clbar.ax.get_yaxis().labelpad = 45  # Does the spacing between number and clbar
# #
# clmap = ax[2].pcolormesh(lon0, lat0, data_interp_mean, vmin=0, vmax=30)
# clbar = plt.colorbar(clmap, ax=ax[2], pad=0.02)
# ax[2].axis('tight')
# clbar.ax.set_ylabel('Interp Mean SSS', rotation=270, fontsize=12)
# clbar.ax.get_yaxis().labelpad = 13  # Does the spacing between number and clbar
# #
# # plt.show()
