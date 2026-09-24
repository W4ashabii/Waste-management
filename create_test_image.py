#!/usr/bin/env python3
"""
Create a simple test image for detection testing.
This creates a minimal valid JPEG file.
"""

import struct

def create_minimal_jpeg(filename="test.jpg"):
    """Create a minimal valid JPEG file for testing."""
    # JPEG SOI marker
    soi = b'\xff\xd8'
    # JPEG EOI marker
    eoi = b'\xff\xd9'
    
    with open(filename, 'wb') as f:
        f.write(soi)
        f.write(eoi)
    
    print(f"Created minimal JPEG file: {filename}")

if __name__ == "__main__":
    create_minimal_jpeg()
