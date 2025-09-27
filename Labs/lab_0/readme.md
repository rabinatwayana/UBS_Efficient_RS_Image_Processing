## Lab 0:

The aim of this lab is to do the following:
- 1. load the image file (Sentinel2 in .SAFE format)
- 2. display its properties (dimensions, resolution)
- 3. display the image


#### Environment Setup

```

conda create -n rsip_env python=3.12
conda activate rsip_env

conda install rasterio=1.4.3-py312hd11fb3f_3, gdal= gdal-3.10.3-py312h06e505a_19,libgdal-jp2openjp=3.10.3-h2bb3654_19, openjpeg = 2.5.3-h036ada5_1, matplotlib=3.10.6-py312hb401068_1
```


Error: 
RasterioIOError: '../../Data/00/S2A_MSIL2A_20250102T183751_N0511_R027_T11SLT_20250102T221646.SAFE/GRANULE/L2A_T11SLT_A049788_20250102T183754/IMG_DATA/R10m/T11SLT_20250102T183751_AOT_10m.jp2' not recognized as being in a supported file format. It could have been recognized by driver JP2OpenJPEG, but plugin gdal_JP2OpenJPEG.dylib is not available in your installation. You may install it with 'conda install -c conda-forge libgdal-jp2openjpeg'

Reason:
What’s happening
Sentinel-2 bands are stored in JPEG2000 (.jp2) format.
GDAL (and Rasterio, which sits on GDAL) needs the JP2OpenJPEG driver to read them.
Your GDAL installation doesn’t have it compiled in (on macOS this is very common).

Solution:
Install JP2 support via conda
conda install -c conda-forge gdal libgdal-jp2openjpeg

