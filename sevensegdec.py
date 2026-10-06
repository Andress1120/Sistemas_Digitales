#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Seven segment decoder: Example script to generate a seven segment decoder
based on a lookup table (LUT). It includes testing and conversion to VHDL/verilog
"""

from myhdl import *
import argparse

# implementation

@block
def sevensegdec(bcd: Signal, sseg: Signal, decod_table: tuple, invert: bool = False):
    """Seven segment decoder"""

    # internal signal for optional bit inversion
    ssegout = Signal(intbv(0)[7:])

    @always_comb
    def logic():
        """LUT implementation: based on a decoder table"""
        ssegout.next = decod_table[int(bcd)]

    @always_comb
    def invertproc():
        """Inverting process for output"""
        if invert:
            sseg.next = ~ssegout
        else:
            sseg.next = ssegout
        
    # this will include logic and invertproc
    return instances()
    
# simulation helper (no checks here: the checks live in test_sevensegdec.py)

@block
def sevensegdec_tb(decod_table: tuple, results: list, invert: bool = False):
    """Testbench: drives all inputs and only RECORDS (input, output) pairs in `results`.
    The pass/fail checking is done outside (pytest) so logic and tests are separated."""

    bcd_tb = Signal(intbv(0)[4:])
    sseg_tb = Signal(intbv(0)[7:])

    uut = sevensegdec(bcd_tb, sseg_tb, decod_table, invert)

    @instance
    def stimulus():
        for bcd_in in range(len(decod_table)):
            bcd_tb.next = bcd_in
            yield delay(10)
            results.append((bcd_in, int(sseg_tb.val)))

    return instances()


def simulate(decod_table: tuple, invert: bool = False, trace: bool = False) -> list:
    """Run the simulation and return a list of (bcd, sseg) tuples."""
    results = []
    tb = sevensegdec_tb(decod_table, results, invert)
    tb.config_sim(trace=trace)
    tb.run_sim()
    tb.quit_sim()
    return results


def check_table(decod_table: tuple, invert: bool = False) -> list:
    """Return the list of mismatches (bcd, expected, read); empty list means OK."""
    mask = 0x7F
    errors = []
    for bcd_in, read in simulate(decod_table, invert):
        expect = (~decod_table[bcd_in] & mask) if invert else decod_table[bcd_in]
        if read != expect:
            errors.append((bcd_in, expect, read))
    return errors

@block
def sevensegdec_nexys(bcd: Signal, sseg: Signal, bcdled: Signal, ssanodes: Signal, decod_table: tuple, invert: bool = False):
    """Envelope for running a demo in the Nexys4 DDR board for the Seven segment decoder"""

    # Main decoder instance
    ssdec = sevensegdec(bcd, sseg, decod_table, invert)

    @always_comb
    def logic():
        """Process to fill the LEDs for switches and display anodes"""
        bcdled.next = bcd
        ssanodes.next = intbv(0xfe)[8:] # only turn on first display, it is turned on with 0.

    # this will include ssdec and logic
    return instances()

def read_table(table_file: str) -> tuple:
    """Read the decoder table from text file:
        * Each line contains a string with 0s and 1s, in order "abcdefg"
        * It must contain 16 lines, one for each 4-bit digit
    """
    if table_file != "":
        try:
            with open(table_file) as f:
                lines = [x.strip() for x in f.readlines() if x.strip() != ""]
            if len(lines) != 16:
                raise ValueError(f"table must have 16 lines, found {len(lines)}")
            if any(len(x) != 7 or set(x) - {"0", "1"} for x in lines):
                raise ValueError("each line must be 7 bits of 0/1 (abcdefg)")
            return tuple([int(x, base=2) for x in lines])
        except Exception as ex:
            print(f"Exception reading the table: {ex}")
    return tuple([0 for x in range(16)])

def run():
    """Entrypoint"""
    parser = argparse.ArgumentParser(description="Seven segment decoder")
    parser.add_argument(
        "--simulation",
        action="store_true",
        help="If enabled, run simulation in python",
    )
    parser.add_argument(
        "--invert",
        action="store_true",
        help="Invert the outputs (simulation only)",
    )
    parser.add_argument(
        "--verilog",
        action="store_true",
        help="Convert to verilog instead of VHDL",
    )
    parser.add_argument(
        "--table",
        type=str,
        default="",
        help="Decoder table to include")
    args = parser.parse_args()

    if args.table != "":
        table = read_table(args.table)
    else:
        print("No table entered, put zero table by default.")
        table = read_table("")

    if args.simulation:
        # simulation (writes sevensegdec_tb.vcd) + consistency check
        for bcd_in, read in simulate(table, args.invert, trace=True):
            print(f"t={bcd_in*10:4d} ns  bcd={bcd_in:2d} ({bcd_in:04b})  sseg(abcdefg)={read:07b}")
        errors = check_table(table, args.invert)
        for bcd_in, expect, read in errors:
            print(f"ERROR: bcd input '{bcd_in}': expected differ {expect:07b} != {read:07b}")
        print("Simulation done." + ("" if errors else " No errors."))

    # conversion

    # Signal list for sevensegdec_nexys
    ss_sig = {
        "bcd": Signal(intbv(0)[4:]),
        "sseg": Signal(intbv(0)[7:]),
        "bcdled": Signal(intbv(0)[4:]),
        "ssanodes": Signal(intbv(0)[8:]),
        "invert": Signal(False),
        "decod_table": table
        }
    sscomponent = sevensegdec_nexys(**ss_sig)

    # which language output
    if args.verilog:
        langout = "verilog"
    else:
        langout = "VHDL"
    sscomponent.convert(hdl=langout)

    print(f"Conversion done ({langout}).")
    
if __name__ == "__main__":
    run()
