#   Copyright 2019 AUI, Inc. Washington DC, USA
#
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.


##########################################
def image_to_zarr(infile, outfile=None, artifacts=None):
    """
    Convert legacy format Image or FITS format image to xarray compatible zarr format image

    This function requires CASA6 casatools module.

    Parameters
    ----------
    infile : str
        Input image filename (.image or .fits format)
    outfile : str
        Output zarr filename. If None, will use infile name with .zarr extension
    artifacts : list of strings
        List of other image artifacts to include if present with infile. Default None = ['mask','model','pb','psf','residual','sumwt']

    Returns
    -------
    """
    from casatools import image as ia
    import numpy as np
    import os
    import time
    from itertools import cycle
    from pandas.io.json._normalize import nested_to_record
    from xarray import Dataset as xd
    from xarray import DataArray as xa
    from numcodecs import Blosc

    print("converting Image...")

    infile = os.path.expanduser(infile)
    prefix = infile[:infile.rindex('.')]
    suffix = infile[infile.rindex('.') + 1:]

    # santize to avoid KeyError when calling imtypes later
    while suffix.endswith('/'):
        suffix = suffix[:-1]

    if outfile == None:
        outfile = prefix + '.zarr'
    else:
        outfile = os.path.expanduser(outfile)
    tmp = os.system("rm -fr " + outfile)
    begin = time.time()

    compressor = Blosc(cname='zstd', clevel=2, shuffle=0)
    IA = ia()

    # all image artifacts will go in same zarr file and share common dimensions if possible
    # check for meta data compatibility
    # store necessary coordinate conversion data
    if artifacts == None:
        imtypes = [suffix] + ['mask', 'model', 'pb', 'psf', 'residual', 'sumwt']
    else:
        imtypes = [suffix] + artifacts
    meta, tm, diftypes, difmeta = {}, {}, [], []
    for imtype in imtypes:
        if os.path.exists(prefix + '.' + imtype):
            rc = IA.open(prefix + '.' + imtype)
            summary = IA.summary(list=False)  # imhead would be better but chokes on big images
            ims = tuple(IA.shape())  # image shape
            coord_names = [ss.replace(' ', '_').lower() for ss in summary['axisnames']]

            # compute world coordinates for spherical dimensions
            # the only way to know is to check the units for angular types (i.e. radians)
            sphr_dims = [dd for dd in range(len(ims)) if summary['axisunits'][dd] == 'rad']
            coord_idxs = np.mgrid[[range(ims[dd]) if dd in sphr_dims else range(1) for dd in range(len(ims))]]
            coord_idxs = coord_idxs.reshape(len(ims), -1)
            coord_world = IA.coordsys().toworldmany(coord_idxs.astype(float))['numeric']
            coord_world = coord_world[sphr_dims].reshape((len(sphr_dims),) + tuple(np.array(ims)[sphr_dims]))
            spi = ['d' + str(dd) for dd in sphr_dims]
            coords = dict([(coord_names[dd], (spi, coord_world[di])) for di, dd in enumerate(sphr_dims)])

            # compute world coordinates for cartesian dimensions
            cart_dims = [dd for dd in range(len(ims)) if dd not in sphr_dims]
            coord_idxs = np.mgrid[[range(ims[dd]) if dd in cart_dims else range(1) for dd in range(len(ims))]]
            coord_idxs = coord_idxs.reshape(len(ims), -1)
            coord_world = IA.coordsys().toworldmany(coord_idxs.astype(float))['numeric']
            coord_world = coord_world[cart_dims].reshape((len(cart_dims),) + tuple(np.array(ims)[cart_dims]))
            for dd, cs in enumerate(list(coord_world)):
                spi = tuple([slice(None) if di == dd else slice(1) for di in range(cs.ndim)])
                coords.update(dict([(coord_names[cart_dims[dd]], cs[spi][0])]))

            # store metadata for later
            tm['coords'] = coords
            tm['dsize'] = np.array(summary['shape'])
            tm['dims'] = [coord_names[di] if di in cart_dims else 'd' + str(di) for di in range(len(ims))]

            # store rest of image meta data as attributes
            omits = ['axisnames', 'incr', 'ndim', 'refpix', 'refval', 'shape', 'tileshape', 'messages']
            nested = [kk for kk in summary.keys() if isinstance(summary[kk], dict)]
            tm['attrs'] = dict([(kk.lower(), summary[kk]) for kk in summary.keys() if kk not in omits + nested])
            tm['attrs'].update(dict([(kk, list(nested_to_record(summary[kk], sep='.').items())) for kk in nested]))

            for msg in summary['messages']:
                line = [tuple(kk.split(':')) for kk in msg.lower().split('\n') if ': ' in kk]
                tm['attrs'].update(dict([(kk[0].strip().replace(' ', '_'), kk[1].strip()) for kk in line]))

            # save metadata from first image product (the image itself)
            # compare later image products to see if dimensions match up
            # Note: only checking image dimensions, NOT COORDINATE VALUES!!
            if meta == {}:
                meta = dict(tm)
            elif np.any(meta['dsize'] != tm['dsize']):
                diftypes += [imtype]
                difmeta += [tm]
                imtypes = [_ for _ in imtypes if _ != imtype]

            rc = IA.close()
        else:
            imtypes = [_ for _ in imtypes if _ != imtype]

    print('compatible components: ', imtypes)
    print('separate components: ', diftypes)

    # process all image artifacts with compatible metadata to same zarr file
    # partition by channel, read each image artifact for each channel
    dsize, chan_dim = meta['dsize'], meta['dims'].index('frequency')
    pt = [-1 for _ in range(len(dsize))]
    for chan in range(dsize[chan_dim]):
        print('processing channel ' + str(chan + 1) + ' of ' + str(dsize[chan_dim]))
        pt[chan_dim] = chan
        chunk_coords = dict(meta['coords'])  # only want one freq channel coord
        chunk_coords['frequency'] = np.array([chunk_coords['frequency'][chan]])
        xdas = {}
        for imtype in imtypes:
            rc = IA.open(prefix + '.' + imtype)
            imchunk = IA.getchunk(pt, pt)
            if imtype == 'fits': imtype = 'image'
            xdas[imtype] = xa(imchunk, dims=meta['dims'])
            rc = IA.close()

        if chan == 0:
            xds = xd(xdas, coords=chunk_coords, attrs=nested_to_record(meta['attrs'], sep='_'))
            encoding = dict(zip(list(xds.data_vars), cycle([{'compressor': compressor}])))
            xds.to_zarr(outfile, mode='w', encoding=encoding)
        else:
            xds = xd(xdas, coords=chunk_coords, attrs=meta['attrs'])
            xds.to_zarr(outfile, mode='a', append_dim='frequency')

    print("processed image size " + str(dsize) + " in " + str(np.float32(time.time() - begin)) + " seconds")

    # process remaining image artifacts with different sizes to different zarr files
    # partition by channel, read each channel for each image artifact
    for nn, imtype in enumerate(diftypes):
        outfile = prefix + '.' + imtype + '.zarr'
        tmp = os.system("rm -fr " + outfile)
        dsize, chan_dim = difmeta[nn]['dsize'], difmeta[nn]['dims'].index('frequency')
        pt = [-1 for _ in range(len(dsize))]
        rc = IA.open(prefix + '.' + imtype)
        for chan in range(dsize[chan_dim]):
            print('processing ' + imtype + ' channel ' + str(chan + 1) + ' of ' + str(dsize[chan_dim]))
            pt[chan_dim] = chan
            chunk_coords = dict(difmeta[nn]['coords'])  # only want one freq channel coord
            chunk_coords['frequency'] = np.array([chunk_coords['frequency'][chan]])

            imchunk = IA.getchunk(pt, pt)
            xda = xa(imchunk, dims=difmeta[nn]['dims'])

            if chan == 0:
                xds = xd({imtype: xda}, coords=chunk_coords, attrs=difmeta[nn]['attrs'])
                encoding = dict(zip(list(xds.data_vars), cycle([{'compressor': compressor}])))
                xds.to_zarr(outfile, mode='w', encoding=encoding)
            else:
                xds = xd({imtype: xda}, coords=chunk_coords, attrs=nested_to_record(difmeta[nn]['attrs'], sep='_'))
                xds.to_zarr(outfile, mode='a', append_dim='frequency')
        rc = IA.close()

    print('complete')

