import logging
from pymem import Pymem
from pymem.process import module_from_name
from pymem.exception import MemoryReadError
import ctypes
from ctypes import windll, Structure, sizeof, byref, c_uint64, c_void_p
from ctypes.wintypes import DWORD
from concurrent.futures import ThreadPoolExecutor
import struct
import time

class MEMORY_BASIC_INFORMATION64(Structure):
    _fields_ = [
        ("BaseAddress", c_uint64),
        ("AllocationBase", c_uint64),
        ("AllocationProtect", DWORD),
        ("__alignment1", DWORD),
        ("RegionSize", c_uint64),
        ("State", DWORD),
        ("Protect", DWORD),
        ("Type", DWORD),
        ("__alignment2", DWORD)
    ]

class MemoryRegion:
    def __init__(self, start: int, size: int, protect: int, type: int):
        self.start = start
        self.size = size
        self.end = start + size
        self.protect = protect
        self.type = type

    @property
    def is_valid_target(self) -> bool:
        return (self.protect in (0x04, 0x40) and  # PAGE_READWRITE or PAGE_EXECUTE_READWRITE
                self.size < 100 * 1024 * 1024)  # Skip very large regions

class Memory:
    # Stats addresses
    strenght_addr = None
    agility_addr = None
    vitality_addr = None
    energy_addr = None
    command_addr = None
    plugin_dll = None
    available_points_addr = None
        
    def __init__(self, config):
        self.logging = logging.getLogger(__name__)
        self.pm = Pymem("megamu.exe")
        self.config = config
        self.load_plugin_module()
        self._chunk_size = 4096 * 256  # 1MB chunks
        self._max_workers = 8
        self.load_memory_addr_from_file()
        
    def load_plugin_module(self):
        self.plugin_dll = module_from_name(self.pm.process_handle, "Plugin.dll").lpBaseOfDll
        
    def get_coordinates(self):
        x = self.pm.read_int(self.plugin_dll + 0x36C6C)
        y = self.pm.read_int(self.plugin_dll + 0x388F0)
        return x, y
    
    def get_level(self):
        return self.pm.read_int(self.plugin_dll + 0x388F4)
    
    def get_reset(self):
        return self.pm.read_int(self.plugin_dll + 0x36C7C)
        

    def _get_memory_regions(self):
        """Get relevant memory regions efficiently"""
        regions = []
        current_address = 0
        
        while current_address < 0x7FFFFFFFFFFFFFFF:
            mbi = MEMORY_BASIC_INFORMATION64()
            
            try:
                result = windll.kernel32.VirtualQueryEx(
                    self.pm.process_handle,
                    c_void_p(current_address),
                    byref(mbi),
                    sizeof(mbi)
                )
                
                if result == 0:
                    break

                if (mbi.State & 0x1000):  # MEM_COMMIT
                    region = MemoryRegion(
                        int(mbi.BaseAddress), 
                        int(mbi.RegionSize),
                        mbi.Protect,
                        mbi.Type
                    )
                    
                    if region.is_valid_target:
                        regions.append(region)
                
                current_address = mbi.BaseAddress + mbi.RegionSize
                if current_address >= 0x7FFFFFFFFFFFFFFF:
                    break
                    
            except Exception as e:
                self.logging.error(f"Error querying memory at 0x{current_address:X}: {str(e)}")
                break

        return regions

    def _scan_region(self, region: MemoryRegion, value: int, progress_callback=None) -> list:
        """Scan a single memory region"""
        matches = []
        value_bytes = struct.pack('<I', value)
        
        try:
            # Read in larger chunks for better performance
            chunk_size = min(region.size, self._chunk_size)
            for offset in range(0, region.size, chunk_size):
                size = min(chunk_size, region.size - offset)
                data = self.pm.read_bytes(region.start + offset, size)
                
                pos = 0
                while True:
                    pos = data.find(value_bytes, pos)
                    if pos == -1:
                        break
                    addr = region.start + offset + pos
                    # Only add non-zero values to matches
                    if value != 0 or self.verify_address(addr):
                        matches.append(addr)
                    pos += 1
                    
            if progress_callback:
                progress_callback(region.size)
                
        except MemoryReadError:
            pass
        except Exception as e:
            self.logging.debug(f"Error scanning region at 0x{region.start:X}: {str(e)}")
            
        return matches

    def verify_address(self, addr: int) -> bool:
        """Verify if an address is valid and stable"""
        try:
            # Read the value multiple times to ensure it's stable
            val1 = self.pm.read_int(addr)
            time.sleep(0.01)
            val2 = self.pm.read_int(addr)
            return val1 == val2 and val1 != 0
        except:
            return False

    def get_value_of_memory(self, address: int) -> int:
        """Read a 4-byte integer value from the specified address"""
        try:
            return self.pm.read_int(address)
        except Exception as e:
            self.logging.error(f"Error reading value at 0x{address:X}: {str(e)}")
            return None

    def first_scan(self, expected_value: int, hex_suffix: str) -> list:
        """Initial memory scan with progress tracking"""
        print(f"Scanning for value {expected_value} with pattern {hex_suffix}...")
        start_time = time.time()
        
        regions = self._get_memory_regions()
        print(f"Found {len(regions)} relevant memory regions to scan")
        
        total_size = sum(region.size for region in regions)
        scanned_size = 0
        
        def update_progress(size):
            nonlocal scanned_size
            scanned_size += size
            progress = int((scanned_size / total_size) * 100)
            print(f"Progress: {progress}%", end='\r')
        
        matches = []
        with ThreadPoolExecutor(max_workers=self._max_workers) as executor:
            futures = []
            for region in regions:
                future = executor.submit(self._scan_region, region, expected_value, update_progress)
                futures.append(future)
            
            for future in futures:
                try:
                    region_matches = future.result()
                    matches.extend(region_matches)
                except Exception as e:
                    self.logging.error(f"Error processing region: {str(e)}")
        
        print(f"\nScan completed in {time.time() - start_time:.2f} seconds")
        
        # Filter addresses by pattern
        pattern_value = int(hex_suffix, 16)
        pattern_length = len(hex_suffix)
        mask = (1 << (pattern_length * 4)) - 1
        
        filtered_matches = [
            addr for addr in matches 
            if addr & mask == pattern_value
        ]
        
        print(f"Found {len(matches)} initial matches")
        print(f"Found {len(filtered_matches)} matches after pattern filtering")
        
        if filtered_matches:
            print("\nResults:")
            for addr in filtered_matches:
                current_value = self.get_value_of_memory(addr)
                print(f"Address: 0x{addr:X}, Current Value: {current_value}")
            
        return filtered_matches if filtered_matches else None
    
    def reuse_scan(self, addresses: list, expected_value: int) -> list:
        """Scan specific memory addresses for a new value"""
        if not addresses:
            print("No addresses provided for reuse_scan.")
            return None

        print(f"Scanning {len(addresses)} addresses for value {expected_value}...")
        start_time = time.time()

        matches = []

        for addr in addresses:
            try:
                value = self.pm.read_int(addr)
                if value == expected_value:
                    matches.append(addr)
            except Exception as e:
                self.logging.error(f"Error reading address 0x{addr:X}: {str(e)}")
                continue

        print(f"\nScan completed in {time.time() - start_time:.2f} seconds")
        print(f"Found {len(matches)} matches")

        if matches:
            print("\nResults:")
            for addr in matches:
                current_value = self.get_value_of_memory(addr)
                print(f"Address: 0x{addr:X}, Current Value: {current_value}")

        return matches if matches else None

    def next_scan(self, expected_value, previous_addresses):
        """Check which addresses from previous scan now contain the new value"""
        if not previous_addresses:
            return None
            
        self.logging.info(f"Checking {len(previous_addresses)} addresses for value: {expected_value}")
        matching_addresses = []
        
        for addr in previous_addresses:
            try:
                value = self.pm.read_int(addr)
                if value == expected_value:
                    matching_addresses.append(addr)
            except Exception:
                continue
                
        return matching_addresses if matching_addresses else None
    
    def another_scan(self, address, value):
        return self.reuse_scan(addresses=address, expected_value=value)

    # Stat-specific search methods
    def find_available_points_memory(self, value):
        return self.first_scan(expected_value=value, hex_suffix="C78")

    def find_str_memory(self, value):
        return self.first_scan(expected_value=value, hex_suffix="D50")
    
    def find_agi_memory(self, value):
        return self.first_scan(expected_value=value, hex_suffix="D54")
    
    def find_vit_memory(self, value):
        return self.first_scan(expected_value=value, hex_suffix="D58")
    
    def find_ene_memory(self, value):
        return self.first_scan(expected_value=value, hex_suffix="D5C")
    
    def find_com_memory(self, value):
        return self.first_scan(expected_value=value, hex_suffix="D60")
    
    def load_memory_addr_from_file(self):
        current_status = self.config.get_memory_status()
        if current_status["current_memory_available_points"]:
            self.available_points_addr = current_status["current_memory_available_points"]
        if current_status["current_memory_strenght"]: 
            self.strenght_addr = current_status["current_memory_strenght"]
        if current_status["current_memory_agility"]: 
            self.agility_addr = current_status["current_memory_agility"]
        if current_status["current_memory_vitality"]: 
            self.vitality_addr = current_status["current_memory_vitality"]
        if current_status["current_memory_energy"]: 
            self.energy_addr = current_status["current_memory_energy"]
        if current_status["current_memory_command"]:
            self.command_addr = current_status["current_memory_command"]

    def set_memory_addr_attr(self, attr, memory_addresses):
        self.logging.debug(f"Updating memory address of {attr} to {memory_addresses}")
        if attr == "available_points":
            self.available_points_addr = memory_addresses
            self.config.update_memory_status("current_memory_available_points", memory_addresses)
        elif attr == "strenght":
            self.strenght_addr = memory_addresses
            self.config.update_memory_status("current_memory_strenght", memory_addresses)
        elif attr == "agility":
            self.agility_addr = memory_addresses
            self.config.update_memory_status("current_memory_agility", memory_addresses)
        elif attr == "vitality":
            self.vitality_addr = memory_addresses
            self.config.update_memory_status("current_memory_vitality", memory_addresses)
        elif attr == "energy":
            self.energy_addr = memory_addresses
            self.config.update_memory_status("current_memory_energy", memory_addresses)
        elif attr == "command":
            self.command_addr = memory_addresses
            self.config.update_memory_status("current_memory_command", memory_addresses)
    
    def all_memory_is_loaded(self, game_class_attributes):
        value = False
        if len(game_class_attributes) == 5 and self.command_addr:
            value = True

        if self.strenght_addr and self.agility_addr and self.vitality_addr and self.energy_addr and self.available_points_addr:
            value = True
        else:
            value = False

        return value
