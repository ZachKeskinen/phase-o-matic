import cdsapi
import numpy as np
import pandas as pd
from shapely import geometry
from pathlib import Path
from datetime import datetime
from typing import Union

def download_era(date: pd.Timestamp, out_dir: Union[str, Path], subset: Union[geometry.Polygon, None], humid_param = 'specific_humidity', LOS: bool = False, overwrite = False) -> Path:
    """
    Download era5 weather model for specific hourly timestep as netcdf. Can be subset to a specific geographic subset.

    Args:
    date: timestamp of the desired date and time. Will be rounded to nearest hour
    out_dir: directory to save file into
    subset: subset geometry to clip data to
    humid_param: relative or specific humidity ('relative_humidity' vs 'specific_humidity')
    LOS: download twice the area to do LOS integrations?
    overwrite: should existing ERA5 files be overwritten?

    returns:
    out_fp: filepath of saved netcdf
    """
    # check to see if era5 token has been saved to .cdsapric file and create client for download
    assert Path('~/.cdsapirc').expanduser().exists(), "Must sign up for ERA5 account and save key to .cdsapric file"
    c = cdsapi.Client()

    # convert out_dir to Path if its a string
    if isinstance(out_dir, str): out_dir = Path(out_dir)

    # expand user and relative paths
    out_dir = out_dir.expanduser().resolve()

    # error check directory to save to
    assert out_dir.exists(), f"Provided directory: {out_dir} does not exist."

    # pressure levels to download (this is all 37 possible) in millibars
    era_pressure_lvls = ['1','2','3','5','7','10','20','30','50', '70','100','125',\
    '150','175','200','225', '250','300','350','400','450','500','550','600','650',\
    '700','750','775','800','825', '850','875','900','925','950','975','1000']

    # try to convert date to pd datetime
    if isinstance(date, str): date = pd.to_datetime(date)

    # error check bounds of date provided
    assert date < datetime.now(date.tzinfo), "provided date is in the future"
    assert date.year > 1939, "provided date is before january 1940"

    # sets options for download
    indict = {'product_type'   :'reanalysis',\
                'format'         :'netcdf',\
                'variable'       :['geopotential','temperature', humid_param],\
                'pressure_level' : era_pressure_lvls, \
                'date'           : date.strftime('%Y-%m-%d'),
                'time'           : date.strftime('%H:00')}

    # name out filepath
    out_fp = out_dir.joinpath(f"ERA5_{date.strftime('%Y-%m-%dT%H:00')}.nc")

    # if a subset was provided. otherwise we are dwonloading everything
    if subset:
        # get bounds
        w, s, e, n = subset.bounds

        # error check bounds
        assert w > -180 and w < 180, f"West bound: {w} is outside of globe"
        assert e > -180 and e < 180, f"East bound: {e} is outside of globe"
        assert n > -90 and n < 90, f"North bound: {n} is outside of globe"
        assert s > -90 and s < 90, f"South bound: {s} is outside of globe"
        
        # expand area by distance across subset if we are gonna try and do line of sight
        if LOS:
            w = np.maximum(w - abs(e - w), -180)
            e = np.minimum(e + abs(e - w), 180)
            s = np.maximum(s - abs(n - s), -90)
            n = np.minimum(n + abs(n - s), 90)
        
        # save to download options
        indict['area'] = f'/'.join([str(b) for b in [n, w, s, e]])

        # change filename to include subset area
        out_fp = out_fp.with_stem(f"{out_fp.stem}_{'_'.join([f'{b:.2f}' for b in [w, s, e, n]])}")

    # if we aren't overwriting then either download or skip and return existing path
    if not out_fp.exists() or overwrite == True:
        c.retrieve('reanalysis-era5-pressure-levels', indict, target = out_fp)
        return out_fp
    else:
        # add logging in here to warn user about not overwriting existing ERA5 file
        return out_fp