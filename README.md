# LiCONiC STX Incubator Shaker Module

A MADSci powered module for controlling LiCONiC STX Incubator Devices. 

This repository contains a LiCONiC interface (liconic_interface.py), a LiCONiC MADSci REST node for the module (liconic_rest_node.py), and resource handling files (resource_tracker.py, resource_types.py, and labware_definitions.py). 

## General Notes

We utlize this module with a LiCONiC STX88 high capacity incubator shaker. Our incubator is configured to have microplate stacks in stacks 1 and 2 and deepwell stacks in stacks 3 and 4. LiCONiC incubators only allow for one stack type by default. In order to utilize our LiCONiC STX88 incubator with both micrplate and deepwell stacks, we needed to customize a cassette configuration file only found in the TCP/IP version of the STX driver on the LiCONiC website. Additionally, we wanted to be able to shake the microplate and deepwell stacks simultaneously at different speeds, which required further customization of the TCP/IP driver.

We used the cross-platform StoreX TCP/IP Driver found [here](https://www.liconic.com/drivers.html).

TODO: add custom shaking driver files to repo

If you have a single stack type in your incubator and do not need custom shaking functions, consider using the StoreX communication library for Windows/Linux/Arm availible at the LiCONiC Drivers website. 

## Run the StoreX TCP/IP Driver

This module and StoreX TCP/IP runs on Windows machines. 

1. Install OpenJDK
    - We use version 1.8.0_372-372

2. Download the StoreX TCP/IP driver and follow the instructions in the installation pdf until you're able to run the driver. Make sure to edit your CassetteConfiguration.xml file if you have more than one stack type in your incubator. 
    
3. Run the TCP/IP driver. This driver must be running in order for the interface or MADSci node provided in this repo to work correctly. 

The TCP/IP driver runs on localhost port 3333 by default. If you changed this port during driver configuration, make note of it for later. 

## Installation 

Before using this LiCONiC REST Node, you will need to clone the module GitHub repo and install the dependencies in a python virtual environment. Use the code below to complete this step. 

General install instructions (using pip):

    # clone the repository
    git clone https://github.com/AD-SDL/liconic_module.git

    # navigate into the liconic_module folder
    cd liconic_module

    # create the virtual environment
    python -m venv .venv

    # activate the virtual environment
    .venv/Scripts/activate

    # install the dependencies 
    pip install -e .

If you wish to install the dependencies using pdm, use the following command:

    # install the dependencies
    pdm install

    
## Running the Interface

The LiCONiC interface (liconic_interface.py) connects to and communicates with the StoreX TCP/IP driver over the port specified durring installation of the TCP/IP driver (default host: "localhost", default port: 3333). 

Test the interface connection with the command below:

    python your\\path\\to\\liconic_interface.py --device <(optional) your COM port> --dll_path <(optional) path to incubator control dll (ComLib.dll)>

--device will default to "COM5" and -dll_path will default to "C:\\Program Files\\INHECO\\Incubator-Control\\ComLib.dll".

Example usage with no optional arguments:

    python inheco_incubator_interface.py

Example usage with optional device argument:

    python inheco_incubator_interface.py --device "COM5" --dll_path "C:\\Program Files\\INHECO\\Incubator-Control\\ComLib.dll"












































