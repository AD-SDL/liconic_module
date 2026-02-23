# LiCONiC STX Incubator Shaker Module

A MADSci powered module for controlling [LiCONiC STX Incubator Devices](https://www.liconic.com/storex.html).

This repository contains a LiCONiC interface (liconic_interface.py), a LiCONiC MADSci REST Node for the module (liconic_rest_node.py), and resource handling files (inventory_handler.py, resource_types.py, and labware_definitions.py).

## General Notes

We utilize this module with a LiCONiC STX88 high-capacity incubator shaker. Our incubator is configured with microplate stacks in stacks 1 and 2 and deepwell stacks in stacks 3 and 4. LiCONiC incubators only allow for one stack type by default. To utilize our LiCONiC STX88 incubator with both microplate and deepwell stacks, we needed to customize a cassette configuration file only found in the TCP/IP version of the STX driver on the LiCONiC website. Additionally, we wanted to be able to shake the microplate and deepwell stacks simultaneously at different speeds, which required further customization of the TCP/IP driver. Please contact LiCONiC for the custom driver functions if you require the ability to control the shakers independently.

We used the cross-platform StoreX TCP/IP Driver found [here](https://www.liconic.com/drivers.html). If you have a single stack type in your incubator and do not need custom shaking functions, consider using the StoreX communication library for Windows/Linux/Arm available at the LiCONiC Drivers website.

## Run the StoreX TCP/IP Driver

This module and StoreX TCP/IP runs on Windows machines.

1. Install OpenJDK
    - We use version 1.8.0_372-372

2. Download the StoreX TCP/IP driver and follow the instructions in the installation PDF until you're able to run the driver. Make sure to edit your CassetteConfig.xml file if you have more than one stack type in your incubator. If you've received any custom driver files from LiCONiC to allow independent control of the shakers, make sure you've copied them into the downloaded TCP/IP driver folder correctly before running the driver.

3. Run the TCP/IP driver. This driver must be running for the interface or MADSci node provided in this repo to work correctly.

The TCP/IP driver runs on localhost port 3333 by default. If you changed this port during driver configuration, make note of it for later.

## Installation

Before using this LiCONiC REST Node, you will need to clone the module GitHub repo and install the dependencies in a Python virtual environment. Use the commands below to complete this step.

General install instructions (using pip):

1. Clone the repository:
    ```sh
    git clone https://github.com/AD-SDL/liconic_module.git
    ```

2. Navigate into the liconic_module folder:
    ```sh
    cd liconic_module
    ```

3. Create the virtual environment:
    ```sh
    python -m venv .venv
    ```

4. Activate the virtual environment:
    ```sh
    .venv/Scripts/activate
    ```

5. Install the dependencies:
    ```sh
    pip install -e .
    ```

If you wish to install the dependencies using pdm, use the following command instead of step 5 above:

    pdm install


## Running the Interface

The LiCONiC interface (liconic_interface.py) connects to and communicates with the StoreX TCP/IP driver over the port specified during installation of the TCP/IP driver (default host: "localhost", default port: 3333).

Test the interface connection with the command below:

    python your\\path\\to\\liconic_interface.py --host <(optional) host location of StoreX TCP/IP driver> --port <(optional) port location of the StoreX TCP/IP driver>

* --host defaults to "localhost"
* --port defaults to 3333

Example usage with no optional arguments:

    python liconic_interface.py

Example usage with optional arguments:

    python liconic_interface.py --host "localhost" --port 3333

"LiCONiC incubator device connected" along with the specified host and port will print to the command line if the interface is able to connect correctly to the device. If connection to the TCP/IP driver fails, a message saying "Error connecting to LiCONiC incubator driver" will print to the command line with the specified host and port and the raised exception.

The link below provides an example Python program which uses the LiCONiC interface to demonstrate key functions such as temperature control and loading/unloading the incubator.

[Example interface usage](examples/example_interface_usage.py)


### Running the REST Node

If you would like to control your STX incubator device through MADSci, you will need to run the MADSci REST Node provided in liconic_rest_node.py.

The MADSci REST Node can be started in the command line using the command below. Make sure to edit the command line arguments to match your driver and REST Node configurations.

    python your\\path\\to\\liconic_rest_node.py --node_url <(optional str) address for your LiCONiC MADSci REST Node> --liconic_driver_host <(optional str) host location of StoreX TCP/IP driver> --liconic_driver_port <(optional int) port location of the StoreX TCP/IP driver>

* --node_url defaults to "http://127.0.0.1:2000"
* --liconic_driver_host defaults to "localhost"
* --liconic_driver_port defaults to 3333

Example usage with no optional arguments (assumes no changes needed to defaults):

    python liconic_rest_node.py


Example usage with all optional arguments:

    python liconic_rest_node.py --node_url "http://127.0.0.1:2005" --liconic_driver_host "localhost" --liconic_driver_port 3333

### Example Usage in MADSci Workflow YAML file

The LiCONiC MADSci REST Node exposes 8 actions to the user: set_target_temp, set_target_humidity, begin_shake, end_shake, load_plate, unload_plate, push_plate_to_conveyor, and pop_plate_from_conveyor.

The link below shows an example of a MADSci Workflow file used to interact with the LiCONiC STX device.

[Example MADSci usage](examples/example_madsci_workflow.yaml)

**set_target_temp** takes a temp float argument, which is the desired incubator temperature in degrees Celsius.

**set_target_humidity** takes a humidity float argument, which is the desired incubator percent humidity.

**begin_shake** takes two arguments: an int shaker_speed and an optional int shaker_id. The shaker_speed argument is the speed at which to shake, and the shaker_id argument defines which shaker(s) will begin shaking. shaker_id value 1 specifies shaker 1 (stacks 1 and 2), 2 specifies shaker 2 (stacks 3 and 4), and None begins shaking both shakers.

**end_shake** takes one optional int shaker_id argument. shaker_id value 1 specifies shaker 1 (stacks 1 and 2), 2 specifies shaker 2 (stacks 3 and 4), and None stops both shakers.

**load_plate** takes four arguments: str plate_type, optional str plate_id, optional int stack, and optional int slot. plate_type refers to the plate types defined in labware_definitions.py ("microplate" and "deep_well" are valid inputs). plate_id allows you to associate an ID with the plate you're loading. stack and slot allow you to load a plate into a specific stack/slot location. If both stack and slot aren't specified, then the plate will be loaded into the next available stack/slot location that is compatible with the specified plate type.

**unload_plate** takes three arguments: optional str plate_id, optional int stack, and optional int slot. You must specify either plate_id or both stack and slot. plate_id allows unloading of a plate by ID. stack and slot allow you to unload plates by location, without the need for plate_id.

**push_plate_to_conveyor** is a utility method meant to aid the use of this MADSci REST Node in local only mode. This method takes three arguments: str plate_type ("microplate" and "deep_well" are valid inputs), optional str plate_name, and optional str liconic_plate_id. This method creates a MADSci resource for the plate based on the user-entered plate_type and pushes that new resource onto the LiCONiC STX conveyor belt slot resource.

**pop_plate_from_conveyor** is a utility method meant to aid the use of this MADSci REST Node in local only mode. This method takes no arguments and simply removes (or pops) any plate MADSci resource that exists on the LiCONiC STX conveyor belt slot resource.
