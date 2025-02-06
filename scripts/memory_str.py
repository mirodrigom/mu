from pymem import Pymem
from pymem.exception import MemoryReadError
import ctypes
from ctypes import windll, Structure, sizeof, byref, c_uint64, c_void_p
from ctypes.wintypes import DWORD
import logging
from concurrent.futures import ThreadPoolExecutor
from typing import List, Tuple
import struct
import time

# Memory constants
MEM_COMMIT = 0x1000
MEM_MAPPED = 0x40000
MEM_PRIVATE = 0x20000
PAGE_READWRITE = 0x04
PAGE_EXECUTE_READWRITE = 0x40

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
        return (self.protect in (PAGE_READWRITE, PAGE_EXECUTE_READWRITE) and 
                self.size < 100 * 1024 * 1024)  # Skip very large regions (>100MB)

class OptimizedMemoryScanner:
    def __init__(self, process_name: str):
        self.pm = Pymem(process_name)
        self.proc = self.pm.process_handle
        self.logger = logging.getLogger(__name__)
        self._chunk_size = 4096 * 256  # 1MB chunks
        self._max_workers = 8

    def get_memory_regions(self) -> List[MemoryRegion]:
        """Get relevant memory regions efficiently"""
        regions = []
        current_address = 0

        while current_address < 0x7FFFFFFFFFFFFFFF:
            mbi = MEMORY_BASIC_INFORMATION64()
            
            try:
                result = windll.kernel32.VirtualQueryEx(
                    self.proc,
                    c_void_p(current_address),
                    byref(mbi),
                    sizeof(mbi)
                )
                
                if result == 0:
                    break

                if (mbi.State & MEM_COMMIT):
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
                self.logger.error(f"Error querying memory at 0x{current_address:X}: {str(e)}")
                break

        return regions

    def _scan_region(self, region: MemoryRegion, value: int, progress_callback=None) -> List[Tuple[int, bytes]]:
        """Optimized region scanning"""
        matches = []
        value_bytes = struct.pack('<I', value)
        
        try:
            # Process region in chunks
            for offset in range(0, region.size, self._chunk_size):
                chunk_size = min(self._chunk_size, region.size - offset)
                data = self.pm.read_bytes(region.start + offset, chunk_size)
                
                # Search for value in chunk
                pos = 0
                while True:
                    pos = data.find(value_bytes, pos)
                    if pos == -1:
                        break
                    addr = region.start + offset + pos
                    matches.append((addr, value_bytes))
                    pos += 1
                    
            if progress_callback:
                progress_callback(region.size)
                
        except MemoryReadError:
            pass  # Skip unreadable regions silently
        except Exception as e:
            self.logger.error(f"Error scanning region at 0x{region.start:X}: {str(e)}")
            
        return matches

    def value_scan(self, value: int, progress_bar=None) -> List[Tuple[int, bytes]]:
        """Parallel memory scan implementation"""
        start_time = time.time()
        regions = self.get_memory_regions()
        print(f"Found {len(regions)} relevant memory regions to scan")
        
        total_size = sum(region.size for region in regions)
        scanned_size = 0
        
        def update_progress(size):
            nonlocal scanned_size
            scanned_size += size
            if progress_bar:
                progress_bar['value'] = int((scanned_size / total_size) * 100)
        
        matches = []
        with ThreadPoolExecutor(max_workers=self._max_workers) as executor:
            future_to_region = {
                executor.submit(self._scan_region, region, value, update_progress): region 
                for region in regions
            }
            
            for future in future_to_region:
                try:
                    region_matches = future.result()
                    matches.extend(region_matches)
                except Exception as e:
                    self.logger.error(f"Error processing region: {str(e)}")
        
        if progress_bar:
            progress_bar['value'] = 100
            
        end_time = time.time()
        print(f"\nScan completed in {end_time - start_time:.2f} seconds")
        return matches

    def filter_addresses(self, addresses: List[Tuple[int, bytes]], pattern: str) -> List[Tuple[int, bytes]]:
        """Filter addresses by hex pattern"""
        if not pattern:
            return addresses
            
        pattern_value = int(pattern, 16)
        pattern_length = len(pattern)
        mask = (1 << (pattern_length * 4)) - 1
        
        return [
            (addr, value) for addr, value in addresses 
            if addr & mask == pattern_value
        ]

    def read_value(self, address: int) -> int:
        """Read a 4-byte integer value from the specified address"""
        try:
            return self.pm.read_int(address)
        except Exception as e:
            self.logger.error(f"Error reading value at 0x{address:X}: {str(e)}")
            return None

def main():
    logging.basicConfig(level=logging.INFO)
    
    scanner = OptimizedMemoryScanner("megamu.exe")
    value_to_find = 15638
    pattern = "D50"
    value_to_find = 2219
    pattern = "C78"
    
    print(f"Scanning for value {value_to_find} with pattern {pattern}...")
    
    class ConsoleProgress:
        def __init__(self):
            self.value = 0
        def __setitem__(self, key, value):
            if key == 'value':
                self.value = value
                print(f"Progress: {value}%", end='\r')
    
    progress_bar = ConsoleProgress()
    
    matches = scanner.value_scan(value_to_find, progress_bar)
    print(f"\nFound {len(matches)} initial matches")
    
    filtered_matches = scanner.filter_addresses(matches, pattern)
    print(f"Found {len(filtered_matches)} matches after pattern filtering")
    
    print("\nResults:")
    for address, _ in filtered_matches:
        current_value = scanner.read_value(address)
        print(f"Address: 0x{address:X}, Current Value: {current_value}")

if __name__ == "__main__":
    main()