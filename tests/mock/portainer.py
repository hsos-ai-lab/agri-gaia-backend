# SPDX-FileCopyrightText: 2024 University of Applied Sciences Osnabrück
# SPDX-FileContributor: Andreas Schliebitz
# SPDX-FileContributor: Henri Graf
# SPDX-FileContributor: Jonas Tüpker
# SPDX-FileContributor: Lukas Hesse
# SPDX-FileContributor: Maik Fruhner
# SPDX-FileContributor: Prof. Dr.-Ing. Heiko Tapken
# SPDX-FileContributor: Tobias Wamhof
#
# SPDX-License-Identifier: AGPL-3.0-or-later

import json
import requests
import datetime
from agri_gaia_backend.services.portainer import portainer_api

from . import common

orig_get = requests.get


def get_endpoints_response_method(endpoint_id):
    def mock_method(*args, **kwargs):
        response = orig_get(*args, **kwargs)
        endpoints = response.json()
        for endpoint in endpoints:
            if endpoint["Id"] == endpoint_id:
                endpoint["LastCheckInDate"] = int(datetime.datetime.now().timestamp())
        response._content = json.dumps(endpoints).encode("utf-8")
        return response

    return mock_method


class DockerContainersMockResponse(common.SuccessfulMockResponse):

    DUMMY_CONTAINER = {
        "Id": "8dfafdbc3a40",
        "Name": "/testcontainer",
        "Image": "ubuntu:latest",
        "ImageID": "d74508fb6632491cea586a1fd7d748dfc5274cd6fdfedee309ecdcbc2bf5cb82",
        "Command": "echo 1",
        "Created": 1367854155,
        "State": "Exited",
        "Status": "Exit 0",
        "Ports": [{"PrivatePort": 2222, "PublicPort": 3333, "Type": "tcp"}],
        "Labels": {
            "com.example.vendor": "Acme",
            "com.example.license": "GPL",
            "com.example.version": "1.0",
        },
        "SizeRw": 12288,
        "SizeRootFs": 0,
        "HostConfig": {"NetworkMode": "default"},
        "NetworkSettings": {
            "Networks": {
                "bridge": {
                    "NetworkID": "7ea29fc1412292a2d7bba362f9253545fecdfa8ce9a6e37dd10ba8bee7129812",
                    "EndpointID": "2cdc4edb1ded3631c81f57966563e5c8525b81121bb3706a9a9a3ae102711f3f",
                    "Gateway": "172.17.0.1",
                    "IPAddress": "172.17.0.2",
                    "IPPrefixLen": 16,
                    "IPv6Gateway": "",
                    "GlobalIPv6Address": "",
                    "GlobalIPv6PrefixLen": 0,
                    "MacAddress": "02:42:ac:11:00:02",
                }
            }
        },
        "Mounts": [
            {
                "Name": "fac362...80535",
                "Source": "/data",
                "Destination": "/data",
                "Driver": "local",
                "Mode": "ro,Z",
                "RW": False,
                "Propagation": "",
            }
        ],
    }

    def __init__(self, json_response=[DUMMY_CONTAINER]):
        super().__init__()
        self.json_response = json_response

    def json(self):
        return self.json_response


class DockerImageCreateMockResponse(common.SuccessfulMockResponse):

    DUMMY_IMAGE_CREATE = {"Id": "", "Warnings": []}

    def __init__(self, json_response=[DUMMY_IMAGE_CREATE]):
        super().__init__()
        self.json_response = json_response

    def json(self):
        return self.json_response


class DockerContainerCreateMockResponse(common.SuccessfulMockResponse):

    DUMMY_CONTAINER_CREATE = {}

    def __init__(self, json_response=[DUMMY_CONTAINER_CREATE]):
        super().__init__()
        self.json_response = json_response

    def json(self):
        return self.json_response


class DockerContainerStartMockResponse(common.SuccessfulMockResponse):

    DUMMY_CONTAINER_START = {}

    def __init__(self, json_response=[DUMMY_CONTAINER_START]):
        super().__init__()
        self.json_response = json_response

    def json(self):
        return self.json_response


class DockerInfoMockResponse(common.SuccessfulMockResponse):
    def __init__(self):
        super().__init__()

    def json(self):
        # from here: https://docs.docker.com/engine/api/v1.41/#operation/SystemInfo
        return {
            "ID": "7TRN:IPZB:QYBB:VPBQ:UMPP:KARE:6ZNR:XE6T:7EWV:PKF4:ZOJD:TPYS",
            "Containers": 14,
            "ContainersRunning": 3,
            "ContainersPaused": 1,
            "ContainersStopped": 10,
            "Images": 508,
            "Driver": "overlay2",
            "DriverStatus": [
                ["Backing Filesystem", "extfs"],
                ["Supports d_type", "true"],
                ["Native Overlay Diff", "true"],
            ],
            "DockerRootDir": "/var/lib/docker",
            "Plugins": {
                "Volume": ["local"],
                "Network": ["bridge", "host", "ipvlan", "macvlan", "null", "overlay"],
                "Authorization": ["img-authz-plugin", "hbm"],
                "Log": [
                    "awslogs",
                    "fluentd",
                    "gcplogs",
                    "gelf",
                    "journald",
                    "json-file",
                    "logentries",
                    "splunk",
                    "syslog",
                ],
            },
            "MemoryLimit": True,
            "SwapLimit": True,
            "KernelMemory": True,
            "KernelMemoryTCP": True,
            "CpuCfsPeriod": True,
            "CpuCfsQuota": True,
            "CPUShares": True,
            "CPUSet": True,
            "PidsLimit": True,
            "OomKillDisable": True,
            "IPv4Forwarding": True,
            "BridgeNfIptables": True,
            "BridgeNfIp6tables": True,
            "Debug": True,
            "NFd": 64,
            "NGoroutines": 174,
            "SystemTime": "2017-08-08T20:28:29.06202363Z",
            "LoggingDriver": "string",
            "CgroupDriver": "cgroupfs",
            "CgroupVersion": "1",
            "NEventsListener": 30,
            "KernelVersion": "4.9.38-moby",
            "OperatingSystem": "Alpine Linux v3.5",
            "OSVersion": "16.04",
            "OSType": "linux",
            "Architecture": "x86_64",
            "NCPU": 4,
            "MemTotal": 2095882240,
            "IndexServerAddress": "https://index.docker.io/v1/",
            "RegistryConfig": {
                "AllowNondistributableArtifactsCIDRs": ["::1/128", "127.0.0.0/8"],
                "AllowNondistributableArtifactsHostnames": [
                    "registry.internal.corp.example.com:3000",
                    "[2001:db8:a0b:12f0::1]:443",
                ],
                "InsecureRegistryCIDRs": ["::1/128", "127.0.0.0/8"],
                "IndexConfigs": {
                    "127.0.0.1:5000": {
                        "Name": "127.0.0.1:5000",
                        "Mirrors": [],
                        "Secure": False,
                        "Official": False,
                    },
                    "[2001:db8:a0b:12f0::1]:80": {
                        "Name": "[2001:db8:a0b:12f0::1]:80",
                        "Mirrors": [],
                        "Secure": False,
                        "Official": False,
                    },
                    "docker.io": {
                        "Name": "docker.io",
                        "Mirrors": ["https://hub-mirror.corp.example.com:5000/"],
                        "Secure": True,
                        "Official": True,
                    },
                    "registry.internal.corp.example.com:3000": {
                        "Name": "registry.internal.corp.example.com:3000",
                        "Mirrors": [],
                        "Secure": False,
                        "Official": False,
                    },
                },
                "Mirrors": [
                    "https://hub-mirror.corp.example.com:5000/",
                    "https://[2001:db8:a0b:12f0::1]/",
                ],
            },
            "GenericResources": [
                {"DiscreteResourceSpec": {"Kind": "SSD", "Value": 3}},
                {"NamedResourceSpec": {"Kind": "GPU", "Value": "UUID1"}},
                {"NamedResourceSpec": {"Kind": "GPU", "Value": "UUID2"}},
            ],
            "HttpProxy": "http://xxxxx:xxxxx@proxy.corp.example.com:8080",
            "HttpsProxy": "https://xxxxx:xxxxx@proxy.corp.example.com:4443",
            "NoProxy": "*.local, 169.254/16",
            "Name": "node5.corp.example.com",
            "Labels": ["storage=ssd", "production"],
            "ExperimentalBuild": True,
            "ServerVersion": "17.06.0-ce",
            "ClusterStore": "consul://consul.corp.example.com:8600/some/path",
            "ClusterAdvertise": "node5.corp.example.com:8000",
            "Runtimes": {
                "runc": {"path": "runc"},
                "runc-master": {"path": "/go/bin/runc"},
                "custom": {
                    "path": "/usr/local/bin/my-oci-runtime",
                    "runtimeArgs": ["--debug", "--systemd-cgroup=false"],
                },
            },
            "DefaultRuntime": "runc",
            "Swarm": {
                "NodeID": "k67qz4598weg5unwwffg6z1m1",
                "NodeAddr": "10.0.0.46",
                "LocalNodeState": "active",
                "ControlAvailable": True,
                "Error": "",
                "RemoteManagers": [
                    {"NodeID": "71izy0goik036k48jg985xnds", "Addr": "10.0.0.158:2377"},
                    {"NodeID": "79y6h1o4gv8n120drcprv5nmc", "Addr": "10.0.0.159:2377"},
                    {"NodeID": "k67qz4598weg5unwwffg6z1m1", "Addr": "10.0.0.46:2377"},
                ],
                "Nodes": 4,
                "Managers": 3,
                "Cluster": {
                    "ID": "abajmipo7b4xz5ip2nrla6b11",
                    "Version": {"Index": 373531},
                    "CreatedAt": "2016-08-18T10:44:24.496525531Z",
                    "UpdatedAt": "2017-08-09T07:09:37.632105588Z",
                    "Spec": {
                        "Name": "default",
                        "Labels": {
                            "com.example.corp.type": "production",
                            "com.example.corp.department": "engineering",
                        },
                        "Orchestration": {"TaskHistoryRetentionLimit": 10},
                        "Raft": {
                            "SnapshotInterval": 10000,
                            "KeepOldSnapshots": 0,
                            "LogEntriesForSlowFollowers": 500,
                            "ElectionTick": 3,
                            "HeartbeatTick": 1,
                        },
                        "Dispatcher": {"HeartbeatPeriod": 5000000000},
                        "CAConfig": {
                            "NodeCertExpiry": 7776000000000000,
                            "ExternalCAs": [
                                {
                                    "Protocol": "cfssl",
                                    "URL": "string",
                                    "Options": {
                                        "property1": "string",
                                        "property2": "string",
                                    },
                                    "CACert": "string",
                                }
                            ],
                            "SigningCACert": "string",
                            "SigningCAKey": "string",
                            "ForceRotate": 0,
                        },
                        "EncryptionConfig": {"AutoLockManagers": False},
                        "TaskDefaults": {
                            "LogDriver": {
                                "Name": "json-file",
                                "Options": {"max-file": "10", "max-size": "100m"},
                            }
                        },
                    },
                    "TLSInfo": {
                        "TrustRoot": "-----BEGIN CERTIFICATE-----\nMIIBajCCARCgAwIBAgIUbYqrLSOSQHoxD8CwG6Bi2PJi9c8wCgYIKoZIzj0EAwIw\nEzERMA8GA1UEAxMIc3dhcm0tY2EwHhcNMTcwNDI0MjE0MzAwWhcNMzcwNDE5MjE0\nMzAwWjATMREwDwYDVQQDEwhzd2FybS1jYTBZMBMGByqGSM49AgEGCCqGSM49AwEH\nA0IABJk/VyMPYdaqDXJb/VXh5n/1Yuv7iNrxV3Qb3l06XD46seovcDWs3IZNV1lf\n3Skyr0ofcchipoiHkXBODojJydSjQjBAMA4GA1UdDwEB/wQEAwIBBjAPBgNVHRMB\nAf8EBTADAQH/MB0GA1UdDgQWBBRUXxuRcnFjDfR/RIAUQab8ZV/n4jAKBggqhkjO\nPQQDAgNIADBFAiAy+JTe6Uc3KyLCMiqGl2GyWGQqQDEcO3/YG36x7om65AIhAJvz\npxv6zFeVEkAEEkqIYi0omA9+CjanB/6Bz4n1uw8H\n-----END CERTIFICATE-----\n",
                        "CertIssuerSubject": "MBMxETAPBgNVBAMTCHN3YXJtLWNh",
                        "CertIssuerPublicKey": "MFkwEwYHKoZIzj0CAQYIKoZIzj0DAQcDQgAEmT9XIw9h1qoNclv9VeHmf/Vi6/uI2vFXdBveXTpcPjqx6i9wNazchk1XWV/dKTKvSh9xyGKmiIeRcE4OiMnJ1A==",
                    },
                    "RootRotationInProgress": False,
                    "DataPathPort": 4789,
                    "DefaultAddrPool": [["10.10.0.0/16", "20.20.0.0/16"]],
                    "SubnetSize": 24,
                },
            },
            "LiveRestoreEnabled": False,
            "Isolation": "default",
            "InitBinary": "docker-init",
            "ContainerdCommit": {
                "ID": "cfb82a876ecc11b5ca0977d1733adbe58599088a",
                "Expected": "2d41c047c83e09a6d61d464906feb2a2f3c52aa4",
            },
            "RuncCommit": {
                "ID": "cfb82a876ecc11b5ca0977d1733adbe58599088a",
                "Expected": "2d41c047c83e09a6d61d464906feb2a2f3c52aa4",
            },
            "InitCommit": {
                "ID": "cfb82a876ecc11b5ca0977d1733adbe58599088a",
                "Expected": "2d41c047c83e09a6d61d464906feb2a2f3c52aa4",
            },
            "SecurityOptions": [
                "name=apparmor",
                "name=seccomp,profile=default",
                "name=selinux",
                "name=userns",
                "name=rootless",
            ],
            "ProductLicense": "Community Engine",
            "DefaultAddressPools": [{"Base": "10.10.0.0/16", "Size": "24"}],
            "Warnings": [
                "WARNING: No memory limit support",
                "WARNING: bridge-nf-call-iptables is disabled",
                "WARNING: bridge-nf-call-ip6tables is disabled",
            ],
        }
