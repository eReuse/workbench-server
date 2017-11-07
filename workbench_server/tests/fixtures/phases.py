phase0 = {
    "created": "2017-04-25T17:55:27.398302",
    "_uuid": "ab1dc8d625a14ed09b7a0aa82f98b6e7",
    "version": "8.0b1",
    "components": [
        {
            "model": "VirtualBox Graphics Adapter",
            "memory": 16.0,
            "@type": "GraphicCard",
            "manufacturer": "InnoTek Systemberatung GmbH"
        },
        {
            "logical_name": "\/dev\/sda",
            "serialNumber": "VB4f81c57d-8b191c53",
            "interface": "ata",
            "model": "VBOX HARDDISK",
            "@type": "HardDrive",
            "size": 4096.0
        },
        {
            "totalSlots": 0,
            "serialNumber": "0",
            "connectors": {
                "firewire": 0,
                "serial": 0,
                "pcmcia": 0,
                "usb": 0
            },
            "model": "VirtualBox",
            "usedSlots": 0,
            "@type": "Motherboard",
            "manufacturer": "Oracle Corporation"
        },
        {
            "model": "82540EM Gigabit Ethernet Controller",
            "serialNumber": "08:00:27:5b:78:01",
            "speed": 1000,
            "@type": "NetworkAdapter",
            "manufacturer": "Intel Corporation"
        },
        {
            "model": "CD-ROM",
            "manufacturer": "VBOX",
            "@type": "OpticalDrive",
            "description": "DVD reader"
        },
        {
            "model": "Intel(R) Core(TM)2 Duo CPU P8600 @ 2.40GHz",
            "manufacturer": "Intel Corp.",
            "benchmark": {
                "score": 4776.0,
                "@type": "BenchmarkProcessor"
            },
            "@type": "Processor",
            "numberOfCores": 1
        }, {
            "model": "82801AA AC'97 Audio Controller",
            "@type": "SoundCard",
            "manufacturer": "Intel Corporation"
        }
    ],
    "device": {
        "serialNumber": "0",
        "_uuid": "c18c14714603477298996eedd83bf513",
        "model": "VirtualBox",
        "type": "Desktop",
        "@type": "Computer",
        "manufacturer": "innotek GmbH"
    },
    "@type": "Snapshot"
}
phase1 = {
    "created": "2017-04-25T17:55:37.651462",
    "_uuid": "ab1dc8d625a14ed09b7a0aa82f98b6e7",
    "version": "8.0b1",
    "components": [
        {
            "model": "VirtualBox Graphics Adapter",
            "memory": 16.0,
            "@type": "GraphicCard",
            "manufacturer": "InnoTek Systemberatung GmbH"
        }, {
            "serialNumber": "VB4f81c57d-8b191c53",
            "benchmark": {
                "readingSpeed": 89.4,
                "@type": "BenchmarkHardDrive",
                "writingSpeed": 39.4
            },
            "interface": "ata",
            "model": "VBOX HARDDISK",
            "@type": "HardDrive",
            "size": 4096.0
        },
        {
            "totalSlots": 0,
            "serialNumber": "0",
            "connectors": {
                "firewire": 0,
                "serial": 0,
                "pcmcia": 0,
                "usb": 0
            },
            "model": "VirtualBox",
            "usedSlots": 0,
            "@type": "Motherboard",
            "manufacturer": "Oracle Corporation"
        },
        {
            "model": "82540EM Gigabit Ethernet Controller",
            "serialNumber": "08:00:27:5b:78:01",
            "speed": 1000,
            "@type": "NetworkAdapter",
            "manufacturer": "Intel Corporation"
        },
        {
            "model": "CD-ROM",
            "manufacturer": "VBOX",
            "@type": "OpticalDrive",
            "description": "DVD reader"
        },
        {
            "model": "Intel(R) Core(TM)2 Duo CPU P8600 @ 2.40GHz",
            "manufacturer": "Intel Corp.",
            "benchmark": {
                "score": 4776.0,
                "@type": "BenchmarkProcessor"
            },
            "@type": "Processor",
            "numberOfCores": 1
        }, {
            "model": "82801AA AC'97 Audio Controller",
            "@type": "SoundCard",
            "manufacturer": "Intel Corporation"
        }
    ],
    "device": {
        "serialNumber": "0",
        "_uuid": "c18c14714603477298996eedd83bf513",
        "model": "VirtualBox",
        "type": "Desktop",
        "@type": "Computer",
        "manufacturer": "innotek GmbH"
    },
    "@type": "Snapshot"
}
phase2 = {
    "created": "2017-04-25T17:55:37.799106",
    "_uuid": "ab1dc8d625a14ed09b7a0aa82f98b6e7",
    "signed_data": None,
    "localpath": "\/tmp\/innotek-gmbh,virtualbox,0.json",
    "filename": "innotek-gmbh,virtualbox,0.json",
    "device": {
        "_uuid": "c18c14714603477298996eedd83bf513"
    }
}
phase3 = {  # copy to usb
    "device": {
        "_uuid": "c18c14714603477298996eedd83bf513"
    },
    "copy_to_usb": False,
    "_uuid": "ab1dc8d625a14ed09b7a0aa82f98b6e7",
    "inventory": None,
    "created": "2017-04-25T17:55:37.843411"
}
phase4 = {  # Stress test
    "device": {
        "_uuid": "c18c14714603477298996eedd83bf513"
    },
    "_uuid": "ab1dc8d625a14ed09b7a0aa82f98b6e7",
    "stress_test_mins": 0,
    "stress_test_ok": True,
    "created": "2017-04-25T17:55:37.871411"
}
phase5 = {  # OS installation
    "device": {
        "_uuid": "c18c14714603477298996eedd83bf513"
    },
    "image_name": "foo-bar",
    "install_image_ok": True,
    "_uuid": "ab1dc8d625a14ed09b7a0aa82f98b6e7",
    "created": "2017-04-25T17:55:37.890987"
}
phases = phase0, phase1, phase2, phase3, phase4, phase5
