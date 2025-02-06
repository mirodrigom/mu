import time
from pymem import Pymem

def scan_memory_range(pm, end_pattern, start_range, end_range, min_value=10, max_value=65000):
    found_addresses = []
    pattern = int(end_pattern, 16)
    
    # Step by 0x1000 to check only addresses that could potentially end in D50
    current_address = (start_range & ~0xFFF) + pattern
    
    print(f"Scanning from 0x{start_range:X} to 0x{end_range:X}")
    print(f"Looking for addresses ending in {end_pattern}")
    
    count = 0
    while current_address < end_range:
        if count % 100000 == 0:  # Update progress less frequently
            print(f"Checking address: 0x{current_address:X}", end='\r')
            
        try:
            value = pm.read_int(current_address)
            if min_value <= value <= max_value:
                found_addresses.append(current_address)
                print(f"\nFound address: 0x{current_address:X}, Value: {value}")
        except:
            pass
            
        current_address += 0x1000  # Move to next potential address ending in D50
        count += 1
            
    print("\nScan complete!")
    return found_addresses

# Attach to the game process
pm = Pymem("megamu.exe")

# Define ranges to check, focusing on areas where addresses were found before
ranges_to_try = [
    (0x2BF00000000, 0x2BF50000000),  # Close range around latest find
    (0x1CFC0000000, 0x1CFD0000000),  # Close range around previous find
]

#str_pattern = "D50"
str_pattern = "C78"

for start_range, end_range in ranges_to_try:
    print(f"\nSearching range 0x{start_range:X} - 0x{end_range:X}")
    str_addresses = scan_memory_range(pm, str_pattern, start_range, end_range)
    
    if str_addresses:
        print("\nFound addresses in this range:")
        for addr in str_addresses:
            try:
                value = pm.read_int(addr)
                if 10 <= value <= max_value:
                    print(f"Address: 0x{addr:X}, Value: {value}")
            except:
                continue