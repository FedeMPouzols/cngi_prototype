#   Copyright 2020 AUI, Inc. Washington DC, USA
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
"""
this module will be included in the api
"""

def auto_uvbin(vis_dataset,auto_uvbin_parms, storage_parms):
    """
    .. todo::
        This function is not yet implemented
    
    An autoflag algorithm that detects outliers on the gridded spatial frequency plane
    (Algorithm prototype exists).
    
    TBD : How can this method call  ngcasa.imaging._make_grid() and also satisfy code structure rules ?
    
    Inputs :
    
    (1) algo parameters
    (2) array name for output flags. Default = FLAG
    (3) array name for input flags. Default = FLAG
    
    If a new flag_array is picked for the output, save only 'new' flags.
    They can be merged with pre-existing flags in a separate step
    
    If an existing flag_array is picked for the output, merge with logical OR.
    
    Returns
    -------
    vis_dataset : xarray.core.dataset.Dataset
    """

