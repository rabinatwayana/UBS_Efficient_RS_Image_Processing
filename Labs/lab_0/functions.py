import rasterio
import os
import glob
import matplotlib.pyplot as plt
import math
import numpy as np
from rasterio.enums import Resampling


def stack_sentinel2_safe(safe_folder, resolution=10, output_file="sentinel2_stack.tif"):

    """
    Reads Sentinel-2 .SAFE folder and stacks bands of chosen resolution into a GeoTIFF.

    Parameters
    ----------
    safe_folder : str
        Path to the .SAFE folder.
    resolution : int
        Band resolution to read (10, 20, or 60 meters).
    out_file : str
        Output stacked GeoTIFF filename.
    """
    # out_file_path=os.path.join(output_folder_path, out_file)
    # Sentinel-2 SAFE stores JP2 files inside GRANULE/*/IMG_DATA/R{resolution}m
    granule_path = os.path.join(safe_folder, "GRANULE")

    # print(band_folder, "band_folder")
    image_path = [f for f in os.listdir(granule_path) if not f.startswith('.')][0]  # usually one granule per SAFE
    band_folder = os.path.join(granule_path,image_path, "IMG_DATA", f"R{resolution}m")

    # Find all bands
    band_files = sorted(glob.glob(os.path.join(band_folder, "*.jp2")))

    if not band_files:
        raise FileNotFoundError(f"No .jp2 files found at resolution {resolution}m")

    print(f"Found {len(band_files)} bands at {resolution}m resolution")
    

    # Open first band as reference
    with rasterio.open(band_files[0]) as src0:
        meta = src0.meta.copy()

    # Update meta to have multiple bands
    meta.update(count=len(band_files))

    # Stack all bands
    with rasterio.open(output_file, 'w', **meta) as dst:
        for i, band_file in enumerate(band_files, start=1):
            with rasterio.open(band_file) as src:
                dst.write(src.read(1), i)

    print(f"Stacked image saved as {output_file}")

def plot_all_bands(tif_path):
    with rasterio.open(tif_path) as src:
        total_bands=src.count
        # Determine subplot grid size
        cols = 4  # number of columns in figure
        rows = math.ceil(total_bands / cols)

        fig, axes = plt.subplots(rows, cols, figsize=(4*cols, 4*rows))
        axes = axes.flatten()  # flatten in case rows*cols > total_bands

        for i in range(total_bands):
            band = src.read(i + 1)  # Rasterio bands are 1-indexed
            vmin, vmax = band.min(), band.max()
            axes[i].imshow(band, cmap='gray', vmin=vmin, vmax=vmax)
            axes[i].set_title(f'Band {i+1}')
            axes[i].axis('off')

        # Hide any extra axes
        for j in range(total_bands, len(axes)):
            axes[j].axis('off')

        plt.tight_layout()
        plt.show()


def plot_rgb_band(tif_path="", red_band_index=2, green_band_index=3, blue_band_index=4):
    with rasterio.open(tif_path) as src:
        red_band = src.read(red_band_index).astype(float)
        green_band = src.read(green_band_index).astype(float)
        blue_band = src.read(blue_band_index).astype(float)
        
        # Normalize bands to 0-1
        def normalize(band):
            return (band - band.min()) / (band.max() - band.min())
        
        red_band = normalize(red_band)
        green_band = normalize(green_band)
        blue_band = normalize(blue_band)
        
        rgb = np.dstack([red_band, green_band, blue_band])
    
    # Plot
    plt.figure(figsize=(10,10))
    plt.imshow(rgb)
    plt.title("Sentinel-2 RGB Composite")
    plt.axis('off')
    plt.show()



def extract_bit_plane(tif_path, band_index, output_file):
    """
    Extract all bit planes from a raster band.

    Parameters:
        tif_path (str): path to raster
        band_index (int): 1-indexed band number
        output_file (str): optional path to save bit planes as GeoTIFF (multi-band)
    """
    with rasterio.open(tif_path) as src:
        band = src.read(band_index)
        dtype_str = str(band.dtype)
        print(f"Original dtype: {dtype_str}")
        bit_depth = int(''.join(filter(str.isdigit, dtype_str)))
        print(f"Bit depth: {bit_depth}")

        # Prepare output array if saving
        if output_file:
            kwargs = src.meta.copy()
            kwargs.update(dtype=rasterio.uint8, count=bit_depth)
            dst = rasterio.open(output_file, 'w', **kwargs)

        for bit in range(bit_depth):
            # Extract current bit plane
            bit_plane = (band >> bit) & 1  # shift by current bit

            # Save bit plane to output file if requested
            if output_file:
                dst.write(bit_plane.astype(np.uint8), bit + 1)

        if output_file:
            dst.close()

    return #bit_plane  # returns the last bit plane by default


def resample_spatial_resolution(input_file, target_resolution, output_file):
    target_resolution = 20  # desired resolution in meters per pixel

    with rasterio.open(input_file) as src:
        # Current pixel size
        src_res_x = src.transform.a
        src_res_y = -src.transform.e

        # Calculate new width and height
        new_width = int(src.width * (src_res_x / target_resolution))
        new_height = int(src.height * (src_res_y / target_resolution))

        # Update metadata
        kwargs = src.meta.copy()
        kwargs.update({
            'width': new_width,
            'height': new_height,
            'transform': src.transform * src.transform.scale(
                (src.width / new_width),
                (src.height / new_height)
            )
        })

        # Write resampled raster
        with rasterio.open(output_file, 'w', **kwargs) as dst:
            for i in range(1, src.count + 1):
                band = src.read(
                    i,
                    out_shape=(new_height, new_width),
                    resampling=Resampling.bilinear  # or Resampling.nearest for categorical
                )
                dst.write(band, i)

    print("Resampled raster saved with resolution:", target_resolution, "m")
    input_size = os.path.getsize(input_file)
    output_size = os.path.getsize(output_file)

    input_size_mb = input_size / (1024 ** 2)
    output_size_mb = output_size / (1024 ** 2)

    print(f"Original file size: {input_size_mb:.2f} MB")
    print(f"File size after resampling: {output_size_mb:.2f} MB")


def reduce_radiometric_resolution(input_file, output_file):
    with rasterio.open(input_file) as src:
        kwargs = src.meta.copy()
        kwargs.update(dtype=rasterio.uint8)  # target 8-bit

        with rasterio.open(output_file, 'w', **kwargs) as dst:
            for i in range(1, src.count + 1):
                band = src.read(i).astype(np.float32)

                # Rescale 0-10000 (typical Sentinel-2 reflectance) to 0-255
                band_scaled = np.clip(band / 10000 * 255, 0, 255).astype(np.uint8)

                dst.write(band_scaled, i)

    print("Saved raster with 8-bit radiometric resolution:", output_file)
    input_size = os.path.getsize(input_file)
    output_size = os.path.getsize(output_file)

    input_size_mb = input_size / (1024 ** 2)
    output_size_mb = output_size / (1024 ** 2)

    print(f"Original file size: {input_size_mb:.2f} MB")
    print(f"File size after reducing radiometric resolution: {output_size_mb:.2f} MB")

def get_properties(file):
    with rasterio.open(file) as src:
        print("Total number of bands: ", src.count)
        print("Cordinate system: ",src.crs)
        print("Data types: ", src.dtypes)
        width, height = src.width, src.height      # number of columns (pixels)
        res_x,res_y = src.transform.a , src.transform.e   # pixel width in CRS units (usually meters)
        print("Image dimensions (width, height): ",  width, height)
        print("Pixel resolution (x, y):", res_x, res_y)