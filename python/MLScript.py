#!/usr/bin/python
#/********************************************************************************
# * Copyright (c) 2014, 2018 Cirrus Link Solutions and others
# *
# * This program and the accompanying materials are made available under the
# * terms of the Eclipse Public License 2.0 which is available at
# * http://www.eclipse.org/legal/epl-2.0.
# *
# * SPDX-License-Identifier: EPL-2.0
# *
# * Contributors:
# *   Cirrus Link Solutions - initial implementation
# ********************************************************************************/
import sys
sys.path.insert(0, "../../../client_libraries/python/")
#print(sys.path)   

import paho.mqtt.client as mqtt
import sparkplug_b as sparkplug
import time
import random
import string

from sparkplug_b import *

# Application Variables
serverUrl = "localhost"
myGroupId = "GROUP"
myNodeName = "NODE"
myDeviceName = "DEVICE"
publishPeriod = 5000
myUsername = "admin"
myPassword = "password"

class AliasMap:
    Next_Server = 0
    Rebirth = 1
    Reboot = 2
    myDocker = 12

######################################################################
# The callback for when the client receives a CONNACK response from the server.
######################################################################
def on_connect(client, userdata, flags, rc):
    if rc == 0:
        print("Connected with result code "+str(rc))
    else:
        print("Failed to connect with result code "+str(rc))
        sys.exit()

    global myGroupId
    global myNodeName

    # Subscribing in on_connect() means that if we lose the connection and
    # reconnect then subscriptions will be renewed.
    client.subscribe("spBv1.0/" + myGroupId + "/NCMD/" + myNodeName + "/#")
    client.subscribe("spBv1.0/" + myGroupId + "/DCMD/" + myNodeName + "/#")
######################################################################

######################################################################
# The callback for when a PUBLISH message is received from the server.
######################################################################
def on_message(client, userdata, msg):
    print("Message arrived for topic: " + msg.topic)
    tokens = msg.topic.split("/")
    if tokens[0] == "spBv1.0" and tokens[1] == myGroupId and (tokens[2] == "NCMD" or tokens[2] == "DCMD") and tokens[3] == myNodeName:
        inboundPayload = sparkplug_b_pb2.Payload()
        inboundPayload.ParseFromString(msg.payload)
        #print(sparkplug_b_pb2.Payload())
        for metric in inboundPayload.metrics:
            print(str(metric))
            if metric.name == "Node Control/Next Server" or metric.alias == AliasMap.Next_Server:
                # 'Node Control/Next Server' is an NCMD used to tell the device/client application to
                # disconnect from the current MQTT server and connect to the next MQTT server in the
                # list of available servers.  This is used for clients that have a pool of MQTT servers
                # to connect to.
                print( "'Node Control/Next Server' is not implemented in this example")
            elif metric.name == "Node Control/Rebirth" or metric.alias == AliasMap.Rebirth:
                # 'Node Control/Rebirth' is an NCMD used to tell the device/client application to resend
                # its full NBIRTH and DBIRTH again.  MQTT Engine will send this NCMD to a device/client
                # application if it receives an NDATA or DDATA with a metric that was not published in the
                # original NBIRTH or DBIRTH.  This is why the application must send all known metrics in
                # its original NBIRTH and DBIRTH messages.
                publishBirth()
            elif metric.name == "Node Control/Reboot" or metric.alias == AliasMap.Reboot:
                # 'Node Control/Reboot' is an NCMD used to tell a device/client application to reboot
                # This can be used for devices that need a full application reset via a soft reboot.
                # In this case, we fake a full reboot with a republishing of the NBIRTH and DBIRTH
                # messages.
                publishBirth()
            elif metric.alias == AliasMap.myDocker:
                # This is a metric we declared in our DBIRTH message and we're emulating an output.
                # So, on incoming 'writes' to the output we must publish a DDATA with the new output
                # value.  If this were a real output we'd write to the output and then read it back
                # before publishing a DDATA message.
                #print(metric.template_value.metrics[0].name)
                # We know this is an Int16 because of how we declated it in the DBIRTH

                #print("CMD message for input/Acknowledge_Y - New Value: {}".format(newValue))

                # Create the DDATA payload - Use the alias because this isn't the DBIRTH
                payload = sparkplug.getDdataPayload()
                template = initTemplateMetric(payload, "myTemplate", AliasMap.myDocker, "Template_V0_1")
                publish = False
                if metric.template_value.metrics[0].name == "input/Acknowledge_Y":
                    newValue = metric.template_value.metrics[0].int_value
                    addMetric(template, "input/Acknowledge_Y", None, MetricDataType.Int16, newValue)
                    publish = True
                if metric.template_value.metrics[0].name == "input/Acknowledge_DT":
                    newValue = metric.template_value.metrics[0].long_value
                    addMetric(template, "input/Acknowledge_DT", None, MetricDataType.DateTime, newValue)
                    publish = True
                if metric.template_value.metrics[0].name == "input/CuttingType_Y":
                    newValue = metric.template_value.metrics[0].string_value
                    addMetric(template, "input/CuttingType_Y", None, MetricDataType.String, newValue)
                    publish = True
                # Publish a message data
                if publish == True:
                    byteArray = bytearray(payload.SerializeToString())
                    pubTopic = "spBv1.0/" + myGroupId + "/DDATA/" + myNodeName + "/" + myDeviceName
                    print("publish new value on topic: " + pubTopic)
                    client.publish(pubTopic, byteArray, 0, False)
            else:
                print( "Unknown command: " + metric.name)
    else:
        print( "Unknown command...")

    print( "Done publishing")
######################################################################

######################################################################
# Publish the BIRTH certificates
######################################################################
def publishBirth():
    publishNodeBirth()
    publishDeviceBirth()
######################################################################

######################################################################
# Publish the NBIRTH certificate
######################################################################
def publishNodeBirth():
    print( "Publishing Node Birth")

    # Create the node birth payload
    payload = sparkplug.getNodeBirthPayload()

    # Set up the Node Controls
    addMetric(payload, "Node Control/Next Server", AliasMap.Next_Server, MetricDataType.Boolean, False)
    addMetric(payload, "Node Control/Rebirth", AliasMap.Rebirth, MetricDataType.Boolean, False)
    addMetric(payload, "Node Control/Reboot", AliasMap.Reboot, MetricDataType.Boolean, False)

    # Create the UDT definition value which includes two UDT members and a single parameter and add it to the payload
    template = initTemplateMetric(payload, "_types_/Template_V0_1", None, None)    # No alias for Template definitions
    # templateParameter = template.parameters.add()
    # templateParameter.name = "Index"
    # templateParameter.type = ParameterDataType.String
    # templateParameter.string_value = "0"
    addMetric(template, "_Configuration", None, MetricDataType.String, "")    # No alias in UDT members
    addMetric(template, "_Status/Alarm_Y", None, MetricDataType.Int16, 0)
    addMetric(template, "_Status/Status_Y", None, MetricDataType.Int16, 0)
    addMetric(template, "output/CuttingDefect_Y", None, MetricDataType.Int16, 0)
    addMetric(template, "input/Acknowledge_DT", None, MetricDataType.DateTime, 0)
    addMetric(template, "input/Acknowledge_Y", None, MetricDataType.Int16, 0)
    addMetric(template, "input/CuttingType_Y", None, MetricDataType.Int16, 0)

    # Publish the node birth certificate
    byteArray = bytearray(payload.SerializeToString())
    client.publish("spBv1.0/" + myGroupId + "/NBIRTH/" + myNodeName, byteArray, 0, False)
######################################################################

######################################################################
# Publish the DBIRTH certificate
######################################################################
def publishDeviceBirth():
    print("Publishing Device Birth")

    # Get the payload
    payload = sparkplug.getDeviceBirthPayload()

    # Create the UDT definition value which includes two UDT members and a single parameter and add it to the payload
    template = initTemplateMetric(payload, "myTemplate", AliasMap.myDocker, "Template_V0_1")
    # templateParameter = template.parameters.add()
    # templateParameter.name = "Index"
    # templateParameter.type = ParameterDataType.String
    # templateParameter.string_value = "1"
    addMetric(template, "_Configuration", None, MetricDataType.String, "")    # No alias in UDT members
    addMetric(template, "_Status/Alarm_Y", None, MetricDataType.Int16, 0)
    addMetric(template, "_Status/Status_Y", None, MetricDataType.Int16, 0)
    addMetric(template, "output/CuttingDefect_Y", None, MetricDataType.Int16, 0)
    addMetric(template, "input/Acknowledge_DT", None, MetricDataType.DateTime, 1647011222)
    addMetric(template, "input/Acknowledge_Y", None, MetricDataType.Int16, 0)
    addMetric(template, "input/CuttingType_Y", None, MetricDataType.String, "cuttingtype")

    # Publish the initial data with the Device BIRTH certificate
    totalByteArray = bytearray(payload.SerializeToString())
    client.publish("spBv1.0/" + myGroupId + "/DBIRTH/" + myNodeName + "/" + myDeviceName, totalByteArray, 0, False)
######################################################################

######################################################################
# Main Application
######################################################################
print("Starting main application")

# Create the node death payload
deathPayload = sparkplug.getNodeDeathPayload()

# Start of main program - Set up the MQTT client connection
client = mqtt.Client(serverUrl, 1883, 60)
client.on_connect = on_connect
client.on_message = on_message
client.username_pw_set(myUsername, myPassword)
deathByteArray = bytearray(deathPayload.SerializeToString())
client.will_set("spBv1.0/" + myGroupId + "/NDEATH/" + myNodeName, deathByteArray, 0, False)
client.connect(serverUrl, 1883, 5)
# Short delay to allow connect callback to occur
time.sleep(.1)
client.loop()

# Publish the birth certificates
publishBirth()

while True:
    # Sit and wait for inbound or outbound events
    for _ in range(5):
        time.sleep(.1)
        client.loop()
######################################################################
