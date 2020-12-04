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

def add_noise():
    """
    .. todo::
        This function is not yet implemented
    
    Add noise to the DATA column of the MS

    Options :
    
    - Gaussian random noise of specified standard-deviation
    - Noise that accounts for delta-T and delta-NU of the observation.
    - Noise that accounts for different antenna collecting areas (from dish diameter meta-data)

    """