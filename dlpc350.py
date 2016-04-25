"""
	This file is part of dlpc350 - A python library to control a DLPC350 DLP Digital Controller
    Copyright (C) 2016 Francesco Valla

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""

from __future__ import division


class SettingsError(Exception):
    def __init__(self, mismatch):
        Exception.__init__(self, mismatch)


class DLPC350:
    """Class meant to control the DPLC350 through USB HID connection"""
    def __init__(self, debug=0, dryrun=0):
        self.debug = debug
        self.dryrun = dryrun
        self.seqN = 0x01
        self.connected = 0

        # Internal Status
        self.status = {'hardware': 0x00,
                       'system': 0x00,
                       'main': 0x00,
                       'displaymode': 0x00,
                       'inputsource': 0x00,
                       'ledRed': 0x00,
                       'ledGreen': 0x00,
                       'ledBlue': 0x00}

        if(dryrun == 0):
            import hid
            self.dlp_hid = hid.device()
        else:
            import fakehid
            self.dlp_hid = fakehid.device()

    def __del__(self):
        self.dlp_hid.close()

    def _int2bytesLSB_(self, n):
        return list(reversed([(n >> i & 0xff) for i in (24, 16, 8, 0)]))

    def _bytes2intLSB_(self, b):
        r = 0x00000000
        for i in (0, 1, 2, 3):
            r |= b[i] << (i * 8)
        return r

    def buildPacket(self, cmd2, cmd3, data=[], readonly=1, reply=1, seq=0):
        reportID = 0x00
        flagsByte = 0b0000000 | readonly << 7 | reply << 6
        if(seq == 0):
            sequenceNumber = 0x00
        else:
            sequenceNumber = self.seqN & 0xFF
            self.seqN += 1
        packetLengthLSB = 2 + len(data)
        packetLengthMSB = packetLengthLSB >> 8
        packetLengthLSB &= 0x00FF
        return map(int, [reportID, flagsByte, sequenceNumber, packetLengthLSB,
                         packetLengthMSB, cmd3, cmd2] + data)

    def dumpPacket(self, pkt, response, cmdString):
        print('[USB HID] SENT: ' + ' '.join('%02x' % i for i in pkt[1:])
              + ' ' + cmdString)
        if response:
            print('[USB HID] RESPONSE: '
                  + ' '.join('%02x' % i for i in response))

    def connectDLP(self):
        try:
            self.dlp_hid.open(vendor_id=0x0451, product_id=0x6401)
            self.connected = 1
            if(self.debug):
                print("Manufacturer: %s" % self.dlp_hid.get_manufacturer_string())
                print("Product: %s" % self.dlp_hid.get_product_string())
                print("Serial No: %s" % self.dlp_hid.get_serial_number_string())
            return 1

        except IOError:
            if(self.debug):
                print("Open failed!")
            return 0

    def getHardwareStatus(self):
        """Hardware Status (CMD2: 0x1A, CMD3: 0x0A)
        The Hardware Status command provides status information on the
        DLPC350's sequencer, DMD controller, and initialization.
        """
        pkt = self.buildPacket(0x1A, 0x0A)
        self.dlp_hid.write(pkt)
        d = self.dlp_hid.read(5)
        if(self.debug):
            self.dumpPacket(pkt, d, '(Hardware Status)')
        return d[4]

    def getSystemStatus(self):
        """System Status (CMD2: 0x1A, CMD3: 0x0B)
        The System Status command provides DLPC350 status on
        internal memory tests.
        """
        pkt = self.buildPacket(0x1A, 0x0B)
        self.dlp_hid.write(pkt)
        d = self.dlp_hid.read(5)
        if(self.debug):
            self.dumpPacket(pkt, d, '(System Status)')
        return d[4]

    def getMainStatus(self):
        """Main Status (CMD2: 0x1A, CMD3: 0x0C)
        The Main Status command provides the status of DMD park and DLPC350
        sequencer, frame buffer, and gamma correction.
        """
        pkt = self.buildPacket(0x1A, 0x0C)
        self.dlp_hid.write(pkt)
        d = self.dlp_hid.read(5)
        if(self.debug):
            self.dumpPacket(pkt, d, '(Main Status)')
        return d[4]

    def softwareReset(self):
        """Software Reset (CMD2: 0x08, CMD3: 0x02)
        This command issues a software reset to the DLPC350, regardless of
        the argument sent.
        """
        pkt = self.buildPacket(0x08, 0x02, data=[0x00], readonly=0, reply=0)
        self.dlp_hid.write(pkt)
        self.dumpPacket(pkt, [], '(Software Reset)')
        return 1

    def enterStandby(self):
        """Power Control (CMD2: 0x02, CMD3: 0x00)
        This command places the DLPC350 in a low-power state and powers down
        the DMD interface. Standby mode should only be enabled after all data
        for the last frame to be displayed has been transferred to the DLPC350.
        Standby mode must be disabled prior to sending any new data.
        """
        pkt = self.buildPacket(0x02, 0x00, data=[0x01], readonly=0, reply=0)
        self.dlp_hid.write(pkt)
        if(self.debug):
            self.dumpPacket(pkt, [], '(enter Standby Mode)')
        return 1

    def exitStandby(self):
        """Power Control (CMD2: 0x02, CMD3: 0x00)
        This command places the DLPC350 in the normal power state and powers
        up the DMD interface.
        """
        pkt = self.buildPacket(0x02, 0x00, data=[0x00], readonly=0, reply=0)
        self.dlp_hid.write(pkt)
        if(self.debug):
            self.dumpPacket(pkt, [], '(exit Standby Mode)')
        return 1

    def getFlashStatus(self):
        """Read Status (CMD2: 0x00, CMD3: 0x00)
        This command returns the current DLPC350 flash status.
        """
        pkt = self.buildPacket(0x00, 0x00, readonly=1, reply=1)
        self.dlp_hid.write(pkt)
        d = self.dlp_hid.read(5)
        self.DisplayMode = d[4]
        if(self.debug):
            self.dumpPacket(pkt, d, '(Get Flash Status)')
        return d[4]

    def forceBufferSwap(self):
        """Force Buffer Swap (CMD2: 0x1A, CMD3: 0x26)
        This command switches between the two internal memory buffers by
        swapping the read and write pointers.
        After a buffer swap, the 24 bit-plane buffer that was streaming data
        to the DMD is now used for input, while the previous 24 bit-plane
        input buffer, now streams data to the DMD. The buffer should be
        frozen before executing this command.
        """
        pkt = self.buildPacket(0x1A, 0x26, data=[0x01], readonly=0, reply=0)
        self.dlp_hid.write(pkt)
        if(self.debug):
            self.dumpPacket(pkt, [], '(Force Buffer Swap)')
        return 1

    def disableBufferSwapping(self):
        """Display Buffer Freeze (CMD2: 0x10, CMD3: 0x0A)
        This command disables swapping the memory buffers.
        When reconfiguring the chipset through a series of commands that change
        the input source or operating mode, TI recommends to issue this command
        to prevent temporary artifacts from reaching the display.
        When the display buffer is frozen, the last image streamed to the DMD
        continues to be displayed.
        """
        pkt = self.buildPacket(0x10, 0x0A, data=[0x01], readonly=0, reply=0)
        self.dlp_hid.write(pkt)
        if(self.debug):
            self.dumpPacket(pkt, [], '(Disable Buffer Swapping)')
        return 1

    def enableBufferSwapping(self):
        """Display Buffer Freeze (CMD2: 0x10, CMD3: 0x0A)
        This command enables swapping the memory buffers.
        """
        pkt = self.buildPacket(0x10, 0x0A, data=[0x00], readonly=0, reply=0)
        self.dlp_hid.write(pkt)
        if(self.debug):
            self.dumpPacket(pkt, [], '(Enable Buffer Swapping)')
        return 1

    def disableBufferWrite(self):
        """Buffer Write Disable (CMD2: 0x1A, CMD3: 0x27)
        This command  prevents the overwriting of the contents of the 48
        bit-planes OR two 24-bit frame buffers of the internal memory buffer.
        """
        pkt = self.buildPacket(0x1A, 0x27, data=[0x01], readonly=0, reply=0)
        self.dlp_hid.write(pkt)
        if(self.debug):
            self.dumpPacket(pkt, [], '(Disable Buffer Write)')
        return 1

    def enableBufferWrite(self):
        """Buffer Write Disable (CMD2: 0x1A, CMD3: 0x27)
        This command  enables the overwriting of the contents of the 48
        bit-planes OR two 24-bit frame buffers of the internal memory buffer.
        """
        pkt = self.buildPacket(0x1A, 0x27, data=[0x00], readonly=0, reply=0)
        self.dlp_hid.write(pkt)
        if(self.debug):
            self.dumpPacket(pkt, [], '(Enable Buffer Write)')
        return 1

    def getCurrentBufferPointer(self):
        """Current Read Buffer Pointer (CMD2: 0x1A, CMD3: 0x28)
        This command returns the pointer to the current internal memory
        buffer whose data is streamed to the DMD.
        """
        pkt = self.buildPacket(0x1A, 0x28, readonly=1, reply=1)
        self.dlp_hid.write(pkt)
        d = self.dlp_hid.read(5)
        if(self.debug):
            self.dumpPacket(pkt, d, '(Current Read Buffer Pointer)')
        return (d[4] & 0x01)

    def getInputSource(self, source=0):
        """Input Source Selection (CMD2: 0x1A, CMD3: 0x00)
        This command returns the current input source.
        """
        pkt = self.buildPacket(0x1A, 0x00, readonly=1, reply=1)
        self.dlp_hid.write(pkt)
        d = self.dlp_hid.read(5)
        self.status['inputsource'] = d[4] & 0x03
        if(self.debug):
            self.dumpPacket(pkt, d, '(Get Input Source)')
        return d[4] & 0x03

    def setInputSource(self, source=0):
        """Input Source Selection (CMD2: 0x1A, CMD3: 0x00)
        The Input Source Selection command selects the input source to be
        displayed by the DLPC350:
        (0) 30-bit parallel port
        (1) Internal Test Pattern
        (2) Flash memory
        (3) FPD-link interface.
        After executing this command, poll the system status using getStatus
        commands.
        """
        pkt = self.buildPacket(0x1A, 0x00, data=[source & 0x03], readonly=0,
                               reply=0)
        self.dlp_hid.write(pkt)
        if(self.debug):
            self.dumpPacket(pkt, [], '(Set Input Source)')
        return 1

    def loadImage(self, index=0):
        """Load Image (CMD2: 0x1A, CMD3: 0x39)
        This command loads an image from flash memory and then performs a
        buffer swap to display the loaded image on the DMD.
        After executing this command, poll the system status using getStatus
        commands.
        """
        pkt = self.buildPacket(0x1A, 0x39, data=[index & 0xFF], readonly=0,
                               reply=0)
        self.dlp_hid.write(pkt)
        if(self.debug):
            self.dumpPacket(pkt, [], '(Load Image)')
        return 1

    def getImageLoadTiming(self, startingIndex=0, imageNumber=1):
        """Image Load Timing (CMD2: 0x1A, CMD3: 0x3A)
        When this command is executed, the system will load the specified
        image and collect the amount of time it took to load that image.
        The busy status of the system will be high until the images have been
        loaded and the timing information is collected.
        This command cannot be executed while the system is already displaying
        patterns from flash.
        """
        pkt = self.buildPacket(0x1A, 0x3A, data=[startingIndex, imageNumber],
                               readonly=0, reply=1)
        self.dlp_hid.write(pkt)
        d = self.dlp_hid.read(8)
        if(self.debug):
            self.dumpPacket(pkt, d, '(Image Load Timing)')
        return self._bytes2intLSB_(d[4:7]) // 18667

    def getDisplayMode(self):
        """Display Mode Selection Command (CMD2: 0x1A, CMD3: 0x1B)
        This command returns the current DLPC350 display mode.
        """
        pkt = self.buildPacket(0x1A, 0x1B, readonly=1, reply=1)
        self.dlp_hid.write(pkt)
        d = self.dlp_hid.read(5)
        self.status['displaymode'] = d[4]
        if(self.debug):
            self.dumpPacket(pkt, d, '(Get Display Mode)')
        return d[4]

    def setDisplayMode(self, mode=0):
        """Display Mode Selection Command (CMD2: 0x1A, CMD3: 0x1B)
        This command enables the DLPC350 internal image processing functions
        for video mode (0) or bypasses them for pattern display mode (1).
        After executing this command, poll the system status using getStatus
        command.
        """
        pkt = self.buildPacket(0x1A, 0x1B, data=[mode & 0x01], readonly=0,
                               reply=0)
        self.dlp_hid.write(pkt)
        if(self.debug):
            self.dumpPacket(pkt, [], '(Display Mode Selection)')
        return 1

    def startValidation(self):
        """Validate Data Command Response (CMD2: 0x1A, CMD3: 0x1A)
        The Validate Data command checks the programmed pattern display
        modes and indicates any invalid settings. This command needs to be
        executed after all pattern display configurations have been completed.
        NOTE: Data to be interpreted only when bit 7 goes from 1 to 0.
        """
        pkt = self.buildPacket(0x1A, 0x1A, data=[0x00], readonly=0, reply=0)
        self.dlp_hid.write(pkt)
        if(self.debug):
            self.dumpPacket(pkt, [], '(Start Validation)')
        return 1

    def getValidationData(self):
        """Validate Data Command Response (CMD2: 0x1A, CMD3: 0x1A)
        The Validate Data command checks the programmed pattern display
        modes and indicates any invalid settings. This command needs to be
        executed after all pattern display configurations have been completed.
        NOTE: Data to be interpreted only when bit 7 goes from 1 to 0.
        """
        pkt = self.buildPacket(0x1A, 0x1A, readonly=1, reply=1)
        self.dlp_hid.write(pkt)
        d = self.dlp_hid.read(5)
        if(self.debug):
            self.dumpPacket(pkt, d, '(Validate Data)')
        return d[4]

    def setPatternTriggerMode(self, mode):
        """Pattern Trigger Mode Selection (CMD2: 0x1A, CMD3: 0x23)
        This command selects between one of the three Pattern Trigger Modes.
        (0) Pattern Trigger Mode 0: VSYNC serves to trigger the pattern display
        sequence
        (1) Pattern Trigger Mode 1: Internally or externally (through TRIG_IN_1
        and TRIG_IN_2) generated trigger
        (2) Pattern Trigger Mode 2: TRIG_IN_1 alternates between two patterns,
        while TRIG_IN_2 advances to the next pair of patterns
        (3) Pattern Trigger Mode 3: Internally or externally generated trigger
        for Variable Exposure display sequence.
        (4) Pattern Trigger Mode 4: VSYNC triggered for Variable Exposure
        display sequence
        Before executing this command, stop the current pattern sequence.
        """
        if(mode > 4):
            if(self.debug):
                print('Invalid pattern trigger mode selected!')
            return -1
        pkt = self.buildPacket(0x1A, 0x23, data=[mode], readonly=0, reply=0,
                               seq=1)
        self.dlp_hid.write(pkt)
        if(self.debug):
            self.dumpPacket(pkt, [], '(Pattern Trigger Mode Selection)')
        return 1

    def setTriggerOut1Control(self, invert_polarity=False, rising_delay=0xBB,
                              falling_delay=0xBB):
        """Trigger Out1 Control (USB: CMD2: 0x1A, CMD3: 0x1D)
        The Trigger Out1 Control command sets the polarity, rising edge
        delay, and falling edge delay of the DLPC350's TRIG_OUT_1 signal.
        The delays are compared to when the pattern is displayed on the DMD.
        Before executing this command, stop the current pattern sequence.
        After executing this command, send the Validation command once before
        starting the pattern sequence.
        """
        if invert_polarity:
            inv = 0x02
        else:
            inv = 0x00
        pkt = self.buildPacket(0x1A, 0x1D, data=[inv, rising_delay,
                                                 falling_delay],
                               readonly=0, reply=0, seq=1)
        self.dlp_hid.write(pkt)
        if(self.debug):
            self.dumpPacket(pkt, [], '(Pattern Trigger Mode Selection)')
        return 1

    def setPatternInputSource(self, source=0x00):
        """Pattern Display Data Input Source (CMD2: 0x1A, CMD3: 0x22)
        The Pattern Display Data Input Source command selects the source of
        the data for pattern display: streaming through the 24-bit RGB/FPD-link
        interface (0b00) or stored data in the flash image memory area from
        external flash (0b11). Before executing this command, stop the current
        pattern sequence. After executing this command, send the Validation
        commands once before starting the pattern sequence.
        """
        if(source not in [0b00, 0b11]):
            if(self.debug):
                print('Invalid pattern input source selected!')
            return -1
        pkt = self.buildPacket(0x1A, 0x22, data=[source], readonly=0, reply=0,
                               seq=1)
        self.dlp_hid.write(pkt)
        if(self.debug):
            self.dumpPacket(pkt, [], '(Pattern Input Data Source Selection)')
        return 1

    def startPatternSequence(self):
        """Pattern Display Start/Stop Pattern Sequence (CMD2: 0x1A, CMD3: 0x24)
        Start Pattern Display Sequence.
        """
        pkt = self.buildPacket(0x1A, 0x24, data=[0x02], readonly=0, reply=0)
        self.dlp_hid.write(pkt)
        if(self.debug):
            self.dumpPacket(pkt, [], '(Start Pattern Sequence)')
        return 1

    def pausePatternSequence(self):
        """Pattern Display Start/Stop Pattern Sequence (CMD2: 0x1A, CMD3: 0x24)
        Pause Pattern Display Sequence. The next Start command will start
        the pattern sequence by re-displaying the current pattern in the
        sequence.
        """
        pkt = self.buildPacket(0x1A, 0x24, data=[0x01], readonly=0, reply=0)
        self.dlp_hid.write(pkt)
        if(self.debug):
            self.dumpPacket(pkt, [], '(Pause Pattern Sequence)')
        return 1

    def stopPatternSequence(self):
        """Pattern Display Start/Stop Pattern Sequence (CMD2: 0x1A, CMD3: 0x24)
        Stop Pattern Display Sequence. The next Start command will restart
        the pattern sequence from the beginning.
        """
        pkt = self.buildPacket(0x1A, 0x24, data=[0x00], readonly=0, reply=0)
        self.dlp_hid.write(pkt)
        if(self.debug):
            self.dumpPacket(pkt, [], '(Stop Pattern Sequence)')
        return 1

    def setPatternExposureTime(self, exposureTime=0x4010, longerFramePeriod=0):
        """Pattern Exposure Time and Frame Period (CMD2: 0x1A, CMD3: 0x29)
        The Pattern Exposure Time and Frame Period dictates the length of
        time a pattern is exposed and the frame period, expressed in us.
        Either the pattern exposure time must be equivalent to the frame period
        or the former must be less than the latter by 230 us.
        Before executing this command, stop the current pattern sequence.
        After executing this command, send the Validation commands once before
        starting the pattern sequence.
        """
        self.exposureTime = self._int2bytesLSB_(exposureTime)
        if(longerFramePeriod == 1):
            self.framePeriod = exposureTime + 230
        else:
            self.framePeriod = exposureTime
        self.framePeriod = self._int2bytesLSB_(self.framePeriod)
        pkt = self.buildPacket(0x1A, 0x29,
                               data=self.exposureTime + self.framePeriod,
                               readonly=0, reply=0, seq=1)
        self.dlp_hid.write(pkt)
        if(self.debug):
            self.dumpPacket(pkt, [], '(Pattern Exposure Time and Frame Period)')
        return 1

    def LUTControl(self, lutEntries=1, repeat=0, nrOfPattern=1, flashImages=1):
        """Pattern Display LUT Control (CMD2: 0x1A, CMD3: 0x31)
        The Pattern Display LUT Control Command controls the execution of
        patterns stored in the lookup table. Before executing this command,
        stop the current pattern sequence. After executing this command,
        send the Validation command once before starting the pattern sequence.
        """
        pkt = self.buildPacket(0x1A, 0x31, data=[
                               ((lutEntries - 1) & 0x7F),
                               (repeat & 0x01),
                               (nrOfPattern - 1),
                               (flashImages - 1) & 0x3F],
                               readonly=0, reply=0, seq=1)
        self.dlp_hid.write(pkt)
        if(self.debug):
            self.dumpPacket(pkt, [], '(Pattern Display LUT Control)')
        return 1

    def setLUTOffsetPointer(self, offset):
        """Pattern Display LUT Offset Pointer (CMD2: 0x1A, CMD3: 0x32)
        The Pattern Display LUT Offset Pointer defines the location of the
        LUT entries in the DLPC350 memory.
        """
        pkt = self.buildPacket(0x1A, 0x32, data=[(offset & 0xFF)], readonly=0,
                               reply=0, seq=1)
        self.dlp_hid.write(pkt)
        if(self.debug):
            self.dumpPacket(pkt, [], '(Set LUT Offset Pointer)')
        return 1

    def openMailbox(self, function):
        """Pattern Display LUT Access Control (CMD2: 0x1A, CMD3: 0x33)
        The LUT on the DLPC350 has a mailbox to send data to different
        registers, and this command selects which register will receive the
        data. To select the flash image indexes or define the patterns used in
        the pattern sequence for the pattern display mode, first open the
        mailbox for the appropriate function by writing the appropriate bit.

        (1) Open the mailbox for image index configuration
        (2) Open the mailbox for pattern definition
        (3) Open the mailbox for variable exposure pattern definition

        Before executing this command, stop the current pattern sequence.
        After executing this command, send the Validation command once before
        starting the pattern sequence.
        """
        if(function not in [1, 2, 3]):
            print('Wrong mailbox function selected!')
            return -1
        pkt = self.buildPacket(0x1A, 0x33, data=[(function & 0x03)],
                               readonly=0, reply=0, seq=1)
        self.dlp_hid.write(pkt)
        if(self.debug):
            self.dumpPacket(pkt, [], '(Open Mailbox)')
        return 1

    def closeMailboxes(self):
        """Pattern Display LUT Access Control (CMD2: 0x1A, CMD3: 0x33)
        Disables (closes) the mailboxes.
        """
        pkt = self.buildPacket(0x1A, 0x33, data=[0x00], readonly=0, reply=0,
                               seq=1)
        self.dlp_hid.write(pkt)
        if(self.debug):
            self.dumpPacket(pkt, [], '(Close Mailboxes)')
        return 1

    def setFlashImageIndexes(self, indexes):
        """Pattern Display LUT Data (CMD2: 0x1A, CMD3: 0x34)
        If the mailbox was opened to define the flash image indexes, list the
        index numbers in the mailbox. For example, if the desired image index
        sequence is 0, 1, 2, 1, then write 0x0 0x1 0x2 0x1 to the mailbox.
        """
        pkt = self.buildPacket(0x1A, 0x34, data=indexes, readonly=0, reply=0,
                               seq=1)
        self.dlp_hid.write(pkt)
        if(self.debug):
            self.dumpPacket(pkt, [], '(Set Flash Image Indexes)')
        return 1

    def fillPatternData(self, data):
        """Pattern Display LUT Data (CMD2: 0x1A, CMD3: 0x34)
        If the mailbox was opened to define the individual patterns, write
        three bytes of data per pattern to the mailbox.
        NOTE: raw LUT data, no control performed on the input array.
        """
        pkt = self.buildPacket(0x1A, 0x34, data=data, readonly=0, reply=0,
                               seq=1)
        self.dlp_hid.write(pkt)
        if(self.debug):
            self.dumpPacket(pkt, [], '(Fill Pattern Data)')
        return 1

    def getLEDOutputEnable(self):
        """LED Enable Outputs (CMD2: 0x1A, CMD3: 0x07)
        This command returns the status of the LED enable pins.
        """
        pkt = self.buildPacket(0x1A, 0x07, readonly=1, reply=1)
        self.dlp_hid.write(pkt)
        d = self.dlp_hid.read(5)
        if(self.debug):
            self.dumpPacket(pkt, d, '(Get LED Output Enable)')
        return d[4]

    def getLEDPWMPolarity(self):
        """LED PWM Polarity (CMD2: 0x1A, CMD3: 0x05)
        This command returns the status of the LED PWM polarities.
        """
        pkt = self.buildPacket(0x1A, 0x05, readonly=1, reply=1)
        self.dlp_hid.write(pkt)
        d = self.dlp_hid.read(5)
        if(self.debug):
            self.dumpPacket(pkt, d, '(Get LED Enable Output)')
        return d[4]

    def getLEDCurrent(self):
        """LED Driver Current Control (CMD2: 0x0B, CMD3: 0x01)
        This command fetches the LED PWM currents as percentages;
        each current is represented by an 8bit value, where 0 means 0%
        and 255 means 100%.
        """
        pkt = self.buildPacket(0x0B, 0x01, readonly=1, reply=1)
        self.dlp_hid.write(pkt)
        d = self.dlp_hid.read(7)
        self.status['ledRed'] = 255 - d[4]
        self.status['ledGreen'] = 255 - d[5]
        self.status['ledBlue'] = 255 - d[6]
        if(self.debug):
            self.dumpPacket(pkt, d, '(Get LED Currents)')
            print("=== LED Currents ===")
            print("RED: %d (%f%%)" % (255 - d[4], ((255 - d[4]) * 100 / 255)))
            print("GREEN: %d (%f%%)" % (255 - d[5], (255 - d[5]) * 100 / 255))
            print("BLUE: %d (%f%%)" % (255 - d[6], (255 - d[6]) * 100 / 255))
        return d[4:6]

    def checkLedCurrent(self, r, g, b, lcrafterChk=1):
        """Check if the LED current settings are safe."""
        if(r > 255 or g > 255 or b > 255):
            print("Invalid current settings given, \
                  values must be between 0 and 255")
            return 0
        totalCurrent = (r * 0.0069) + (g * 0.0071) + (b * 0.0063) + 0.9611
        if(lcrafterChk and totalCurrent > 4.2):
            print("Total LED current exceding 4.3A!")
            return 0
        if(self.debug):
            print("Total LED current: %fA" % totalCurrent)
        return 1

    def setLEDCurrent(self, r=151, g=120, b=125):
        """LED Driver Current Control (CMD2: 0x0B, CMD3: 0x01)
        This command controls the pulse duration of the specific LED PWM
        output pin. The PWM value can be set from 0 to 100% in 256 steps.
        If the LED PWM polarity is set to normal polarity, a setting of 0xFF
        gives the maximum PWM current.
        NOTE: The LED current is a function of the specific LED driver design;
        for example, the DLP Lightcrafter 4500 computes the currents as follows:
            - Red LED Current (A) = 0.0175 x (LED Current Value) + 0.4495
            - Green LED Current (A) = 0.0181 x (LED Current Value) + 0.3587
            - Blue LED Current (A) = 0.0160 x (LED Current Value) + 0.1529
        """
        if(self.checkLedCurrent(r, g, b) == 1):
            currents = [255 - r, 255 - g, 255 - b]
            pkt = self.buildPacket(0x0B, 0x01, data=currents,
                                   readonly=0, reply=0)
            self.dlp_hid.write(pkt)
            if(self.debug):
                    self.dumpPacket(pkt, [], '(Set LED Current)')
        return 1

    def configureGPIO(self, pin, state=0, buffertype=0, direction=1, disable=0):
        """The GPIO Configuration command enables GPIO functionality on a
        specific set of DLPC350 pins. The command sets their direction,
        output buffer type, and output state.
        Parameters:
            * pin: pin number
            * state: output state (0 = low, 1 = high)
            * buffertype: output buffer type (0 = standard, 1 = open-drain)
            * direction: pin direction (0 = input, 1 = output)
            * disable: GPIO disable (0 = GPIO function, 1 = alternate function)
        """
        cfg = 0x00 | ((state & 0x01) << 3) | ((buffertype & 0x01) << 4) | \
            ((direction & 0x01) << 5) | ((disable & 0x01) << 7)
        config = [pin & 0xFF, cfg]
        pkt = self.buildPacket(0x1A, 0x38, data=config, readonly=0, reply=0)
        self.dlp_hid.write(pkt)
        if(self.debug):
                self.dumpPacket(pkt, [], '(Configure GPIO)')
        return 1

    def readGPIO(self, pin):
        """The GPIO Configuration command enables GPIO functionality on a
        specific set of DLPC350 pins. The command sets their direction,
        output buffer type, and output state.
        Parameters:
            * pin: pin number
        """
        config = [pin & 0xFF]
        pkt = self.buildPacket(0x1A, 0x38, data=config, readonly=1, reply=1)
        self.dlp_hid.write(pkt)
        d = self.dlp_hid.read(6)
        if(self.debug):
                self.dumpPacket(pkt, d, '(Read GPIO)')
        return d[5]

    # Higher-level commands #
    def getStatus(self):
        """Gets the status of the system. Returns 1 when the system is in a
        "safe" status, 0 otherwise.
        """
        self.status['hardware'] = self.getHardwareStatus()
        self.status['system'] = self.getSystemStatus()
        self.status['main'] = self.getMainStatus()

        if(self.status['hardware'] == 0x01 and self.status['system'] == 0x01):
            return 1

        if(self.debug):
            # Hardware status
            print("=== Hardware Status ===")
            print("Internal initialization: "
                  + ("OK" if (self.status['hardware'] & 0x01) else "Error"))
            print("DMD Reset Controller:    "
                  + ("OK" if not (self.status['hardware'] & 0x04) else "Error"))
            print("Forced Swap:             "
                  + ("OK" if not (self.status['hardware'] & 0x08) else "Error"))
            print("Sequencer Abort:         "
                  + ("OK" if not (self.status['hardware'] & 0x40) else "Error"))
            print("Sequencer:               "
                  + ("OK" if not (self.status['hardware'] & 0x80) else "Error"))
            # System status
            print("=== System Status ===")
            print("Internal Memory Test:    "
                  + ("Passed" if (self.status['system'] & 0x01) else "Failed"))
            # Main status
            print("=== Main Status ===")
            print("DMD Park Status:         "
                  + ("Parked" if (self.status['main'] & 0x01) else "Not parked"))
            print("Sequencer Run Flag:      "
                  + ("Running" if (self.status['main'] & 0x02) else "Stopped"))
            print("Frame Buffer Swap Flag:  "
                  + ("Frozen" if (self.status['main'] & 0x04) else "Not frozen"))
            print("Gamma Correction Func:   "
                  + ("Enabled" if (self.status['main'] & 0x40) else "Disabled"))

        return 0

    def pollForStatusOK(self, timeout=10):
        k = 0
        status = 0
        while(not status and k < timeout):
            status = self.getStatus()
            k += 1
        return status

    def validateSequence(self):
        """Sends the validation command and polls for valid validation data."""
        if(self.debug):
            print("Validating sequence..."),
        self.startValidation()
        d = self.getValidationData()
        while((d >> 7) == 1):
            # time.sleep(0.001)
            d = self.getValidationData()

        if(self.debug and d == 0):
            print("OK!")
        elif(d):
            print("Validation Error")

        if((d >> 0) & 0x01):
            print("Selected exposure or frame period settings are invalid")

        if((d >> 1) & 0x01):
            print("Selected pattern numbers in LUT are invalid")

        if((d >> 2) & 0x01):
            print("Continuous Trigger Out1 request or overlapping black sectors")

        if((d >> 3) & 0x01):
            print("Post vector was not inserted prior to external triggered vector")

        if((d >> 4) & 0x01):
            print("Frame period or exposure difference is less than 230usec")

        return d

    def sendPatternSequence(self, sequence=[0x00, 0x21, 0x06],
                            flashIndexes=[0x08], displayTime=100000,
                            triggerMode=1, repeat=0):
        """Sends a pattern sequence.
        Parameters:
            * sequence: pattern sequence.
            * flashIndexes: indexes of flash images used in the sequence.
            * displayTime: exposure time for each pattern.
            * triggerMode: trigger mode (see TI documentation for details).
            * repeat: repeat sequence.
        """
        nrOfLUTEntries = len(sequence) // 3
        nrOfFlashImages = len(flashIndexes)
        if len(sequence) % 3 or not nrOfLUTEntries:
            raise SettingsError("Invalid pattern sequence!")
        if not nrOfFlashImages or nrOfFlashImages > nrOfLUTEntries:
            raise SettingsError("Invalid number of Flash images!")

        self.setPatternInputSource(source=3)  # Input source: flash
        self.LUTControl(lutEntries=nrOfLUTEntries, repeat=repeat,
                        nrOfPattern=nrOfLUTEntries, flashImages=nrOfFlashImages)
        self.setPatternExposureTime(exposureTime=displayTime, longerFramePeriod=0)
        self.setPatternTriggerMode(mode=triggerMode)
        self.openMailbox(function=2)
        self.setLUTOffsetPointer(0)
        self.fillPatternData(sequence)
        self.closeMailboxes()
        self.openMailbox(function=1)
        self.setLUTOffsetPointer(0)
        self.setFlashImageIndexes(flashIndexes)
        self.closeMailboxes()
