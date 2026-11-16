"""Pytest fixtures and synthetic Linux command output mocks."""
import pytest

MOCK_LSCPU_JSON = """{
   "lscpu": [
      {"field": "Architecture:", "data": "x86_64"},
      {"field": "CPU op-mode(s):", "data": "32-bit, 64-bit"},
      {"field": "Address sizes:", "data": "39 bits physical, 48 bits virtual"},
      {"field": "Byte Order:", "data": "Little Endian"},
      {"field": "CPU(s):", "data": "16"},
      {"field": "On-line CPU(s) list:", "data": "0-15"},
      {"field": "Vendor ID:", "data": "AuthenticAMD"},
      {"field": "Model name:", "data": "AMD Ryzen 7 5800H with Radeon Graphics"},
      {"field": "CPU family:", "data": "25"},
      {"field": "Model:", "data": "80"},
      {"field": "Thread(s) per core:", "data": "2"},
      {"field": "Core(s) per socket:", "data": "8"},
      {"field": "Socket(s):", "data": "1"},
      {"field": "Stepping:", "data": "0"},
      {"field": "CPU max MHz:", "data": "4462.5000"},
      {"field": "CPU min MHz:", "data": "1200.0000"},
      {"field": "BogoMIPS:", "data": "6388.00"},
      {"field": "Virtualization:", "data": "AMD-V"}
   ]
}"""

MOCK_LSCPU_TEXT = """Architecture:                    x86_64
CPU op-mode(s):                  32-bit, 64-bit
Address sizes:                   39 bits physical, 48 bits virtual
Byte Order:                      Little Endian
CPU(s):                          20
On-line CPU(s) list:             0-19
Vendor ID:                       GenuineIntel
Model name:                      12th Gen Intel(R) Core(TM) i7-12700H
Thread(s) per core:              2
Core(s) per socket:              14
Socket(s):                       1
CPU max MHz:                     4700.0000
CPU min MHz:                     400.0000
Virtualization:                  VT-x
"""

MOCK_PROC_CPUINFO = """processor	: 0
vendor_id	: GenuineIntel
cpu family	: 6
model		: 154
model name	: 12th Gen Intel(R) Core(TM) i7-12700H
stepping	: 3
cpu MHz		: 2300.000
cache size	: 24576 KB
physical id	: 0
siblings	: 20
core id		: 0
cpu cores	: 14
flags		: fpu vme de pse tsc msr pae mce cx8 apic sep mtrr pge mca cmov pat pse36 clflush dts acpi mmx fxsr sse sse2 ss ht tm pbe syscall nx pdpe1gb rdtscp lm constant_tsc art arch_perfmon pebs bts rep_good nopl xtopology nonstop_tsc cpuid aperfmperf tsc_known_freq pni pclmulqdq dtes64 monitor ds_cpl vmx smx est tm2 ssse3 sdbg fma cx16 xtpr pdcm pcid sse4_1 sse4_2 x2apic movbe popcnt tsc_deadline_timer aes xsave avx f16c rdrand lahf_lm abm 3dnowprefetch cpuid_fault epb ssbd ibrs ibpb stibp ibrs_enhanced tpr_shadow vnmi flexpriority ept vpid ept_ad fsgsbase tsc_adjust bmi1 avx2 smep bmi2 erms invpcid rdseed adx smap clflushopt clwb intel_pt sha_ni xsaveopt xsave cflush xsaves split_lock_detect avx_vnni dtherm ida arat pln pts hwp hwp_notify hwp_act_window hwp_epp hwp_pkg_req umip pku ospke waitpkg gfni vaes vpclmulqdq rdpid movdiri movdir64b fsrm md_clear serialize pconfig arch_lbr flush_l1d arch_capabilities

processor	: 1
vendor_id	: GenuineIntel
cpu family	: 6
model		: 154
model name	: 12th Gen Intel(R) Core(TM) i7-12700H
stepping	: 3
cpu MHz		: 2300.000
core id		: 1
cpu cores	: 14
flags		: fpu vmx lm
"""

MOCK_FREE_B = """               total        used        free      shared  buff/cache   available
Mem:     16568852480  6488248320  4829392896   528175104  5251211264  9552429056
Swap:     4294967296           0  4294967296
"""

MOCK_PROC_MEMINFO = """MemTotal:       16180520 kB
MemFree:         4716204 kB
MemAvailable:    9328544 kB
Buffers:          345120 kB
Cached:          4785864 kB
SwapCached:            0 kB
Active:          5912400 kB
Inactive:        4312100 kB
SwapTotal:       4194300 kB
SwapFree:        4194300 kB
"""

MOCK_LSPCI_DUAL_GPU = """00:00.0 Host bridge: Intel Corporation Alder Lake Host Bridge/DRAM Registers (rev 02)
00:02.0 VGA compatible controller: Intel Corporation Alder Lake-P Integrated Graphics Controller (rev 0c)
00:14.0 USB controller: Intel Corporation Alder Lake PCH USB 3.2 Gen 2x1 xHCI Host Controller (rev 01)
01:00.0 3D controller: NVIDIA Corporation GA107M [GeForce RTX 3050 Mobile] (rev a1)
"""

MOCK_LSPCI_AMD = """00:00.0 Host bridge: Advanced Micro Devices, Inc. [AMD] Renoir/Cezanne Root Complex
04:00.0 VGA compatible controller: Advanced Micro Devices, Inc. [AMD/ATI] Cezanne [Radeon Vega Series / Radeon Vega Mobile Series] (rev c5)
"""

MOCK_LSBLK_JSON = """{
   "blockdevices": [
      {
         "name": "nvme0n1",
         "size": 1000204886016,
         "type": "disk",
         "fstype": null,
         "mountpoint": null,
         "rota": false,
         "tran": "nvme",
         "model": "Samsung SSD 980 PRO 1TB",
         "children": [
            {
               "name": "nvme0n1p1",
               "size": 536870912,
               "type": "part",
               "fstype": "vfat",
               "mountpoint": "/boot/efi",
               "rota": false,
               "tran": null,
               "model": null
            },
            {
               "name": "nvme0n1p2",
               "size": 999668015104,
               "type": "part",
               "fstype": "ext4",
               "mountpoint": "/",
               "rota": false,
               "tran": null,
               "model": null
            }
         ]
      },
      {
         "name": "sda",
         "size": 2000398934016,
         "type": "disk",
         "fstype": null,
         "mountpoint": null,
         "rota": true,
         "tran": "sata",
         "model": "ST2000LM015-2E8174",
         "children": [
            {
               "name": "sda1",
               "size": 2000397885440,
               "type": "part",
               "fstype": "ext4",
               "mountpoint": "/data",
               "rota": true,
               "tran": null,
               "model": null
            }
         ]
      }
   ]
}"""

MOCK_DMIDECODE_MOTHERBOARD = """# dmidecode 3.4
Getting SMBIOS data from sysfs.
SMBIOS 3.3.0 present.

Handle 0x0000, DMI type 0, 26 bytes
BIOS Information
	Vendor: LENOVO
	Version: H1ET45WW (1.23 )
	Release Date: 08/10/2023
	Address: 0xE0000
	Runtime Size: 128 kB
	ROM Size: 32 MB

Handle 0x0002, DMI type 2, 17 bytes
Base Board Information
	Manufacturer: LENOVO
	Product Name: 21CVCTO1WW
	Version: SDK0T76538 WIN
	Serial Number: MP2ABC123
"""

MOCK_DMIDECODE_MEMORY = """# dmidecode 3.4
Handle 0x002A, DMI type 16, 23 bytes
Physical Memory Array
	Location: System Board
	Use: System Memory
	Error Correction Type: None
	Maximum Capacity: 32 GB
	Error Information Handle: Not Provided
	Number Of Devices: 2

Handle 0x002B, DMI type 17, 92 bytes
Memory Device
	Array Handle: 0x002A
	Size: 16 GB
	Form Factor: SODIMM
	Set: None
	Locator: Controller0-ChannelA-DIMM0
	Bank Locator: BANK 0
	Type: DDR4
	Type Detail: Synchronous Unbuffered
	Speed: 3200 MT/s
	Manufacturer: Samsung
	Part Number: M471A2K43EB1-CWE

Handle 0x002C, DMI type 17, 92 bytes
Memory Device
	Array Handle: 0x002A
	Size: No Module Installed
	Form Factor: Unknown
	Set: None
	Locator: Controller0-ChannelB-DIMM0
	Bank Locator: BANK 1
	Type: Unknown
"""
