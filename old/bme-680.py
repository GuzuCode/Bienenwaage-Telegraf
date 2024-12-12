import bme680

# Kein except-Block, um den kompletten Traceback in stdout/stderr zu sehen
sensor = bme680.BME680(bme680.I2C_ADDR_SECONDARY)
sensor.set_humidity_oversample(bme680.OS_2X)
sensor.set_pressure_oversample(bme680.OS_4X)
sensor.set_temperature_oversample(bme680.OS_8X)
sensor.set_filter(bme680.FILTER_SIZE_3)
sensor.set_gas_status(bme680.ENABLE_GAS_MEAS)

if sensor.get_sensor_data():
    temp = float(sensor.data.temperature)
    pressure = float(sensor.data.pressure)
    humidity = float(sensor.data.humidity)
    gas_resistance = (
        float(sensor.data.gas_resistance)
        if sensor.data.heat_stable
        else None
    )

    line_protocol = f"bme680 temperature={temp},pressure={pressure},humidity={humidity}"
    if gas_resistance is not None:
        line_protocol += f",gas_resistance={gas_resistance}"
    print(line_protocol)