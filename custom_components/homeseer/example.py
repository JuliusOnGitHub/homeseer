import aiohttp
import asyncio
import logging
import libhomeseer
import sys

async def main():

    # if len(sys.argv) < 2:
    #     print("Usage: python example.py ipaddress")
    #     exit(1)

    # host = sys.argv[1]
    host = "10.0.0.19"
    websession = aiohttp.ClientSession()

    # Create an instance of the HomeSeer class by calling its constructor with (at minimum) host and websession
    # host is a string containing the IP address of the HomeSeer software installation
    # websession is an instance of aiohttp.ClientSession
    # You must also pass username, password, http_port, and ascii_port to the constructor if these are not the defaults
    # username = "default", password = "default", http_port = 80, ascii_port = 11000
    homeseer = libhomeseer.HomeSeer(host, websession, "homeassistant", "homeassistant")

    # libhomeseer does not implement asyncio timeouts directly so your implementation must provide for timeouts
    timeout = 10

    # Initialize the HomeSeer connection by awaiting HomeSeer.initialize()
    # HomeSeer.initialize() populates HomeSeer.devices and HomeSeer.events
    # HomeSeer.devices is a dict of (supported) device objects indexed by ref
    # HomeSeer.events is a list of event objects
    try:
        await asyncio.wait_for(homeseer.initialize(), timeout)
    except asyncio.TimeoutError:
        print(f"Error connecting to HomeSeer at {host}")
        return

    # Not all HomeSeer devices are fully supported in libhomeseer yet
    # Devices with as-yet unsupported control pairs will be reported in debug logging
    # Device attributes (ref, value, status, etc.) are represented as properties of the device object
    # Certain device classes feature methods to control the device based on its detected Control Pairs:
    # HomeSeerSwitchableDevice - device.on() and device.off()
    # HomeSeerDimmableDevice - device.on(), device.off(), and device.dim(0-100)
    # HomeSeerLockableDevice - device.lock() and device.unlock()
    print()
    print("-----------------")
    print("HomeSeer Devices:")
    print("-----------------")
    for device in homeseer.devices.values():
        if isinstance(device, libhomeseer.devices.HomeSeerCoverDevice):
            print(
                f"{device.location2} {device.location} {device.name} "
                f"(Type: {device.device_type_string}, Ref: {device.ref}) (libhomeseer type: {type(device)})"
            )

    # Start the ASCII listener by awaiting HomeSeer.start_listener()
    # Stop the ASCII listener by awaiting HomeSeer.stop_listener()
    print()
    print("Starting HomeSeer ASCII listener...")
    await homeseer.start_listener()

logging.basicConfig(level=logging.INFO)
loop = asyncio.get_event_loop()
loop.create_task(main())
loop.run_forever()
