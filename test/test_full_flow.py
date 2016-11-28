import os
from IPython.core.payload import PayloadManager
os.chdir('../src')
import sys
sys.path.append(os.getcwd())
import unittest
__unittest = True
import waveConvertVars as wcv
import waveconverterEngine as weng
from gnuradio import eng_notation
from protocol_lib import ProtocolDefinition, getNextProtocolId
from protocol_lib import protocolSession
from protocol_lib import fetchProtocol
from waveconverterEngine import demodIQFile
from waveconverterEngine import buildTxList
from waveconverterEngine import decodeAllTx
from statEngine import computeStats
from statEngine import buildStatStrings

class TestFullFlow(unittest.TestCase):
    def loadBasicTestParameters(self):
        self.verbose = False
        self.samp_rate = 8e6
        self.basebandSampleRate = 100e3
        self.center_freq = 303e6
        self.iqFileName = "/media/paul/bulkdata/factorialabs/rfsiglib/fan_control/pc_iq/fan_all_dip1101_c303M_s8M.iq"
        self.waveformFileName = ""
        self.outputHex = False
        self.timingError = 0.2
        self.showAllTx = False
        self.timeBetweenTx = 3000
        self.timeBetweenTx_samp = self.timeBetweenTx * self.basebandSampleRate / 1e6
        self.frequency = 304.48e6
        self.glitchFilterCount = 2
        self.threshold = 0.05
        
        # set up globals
        wcv.samp_rate = self.samp_rate
        wcv.basebandSampleRate = self.basebandSampleRate
        
        # load protocol
        self.protocol = fetchProtocol(7)
        
        return(0)
        
    def loadExpectedData(self):
        # build list of expected values
        self.expectedPayloadData = []
        for n in xrange(15):
            self.expectedPayloadData.append([1, 1, 1, 0, 1, 0, 1, 0, 0, 0, 0, 0])
        for n in xrange(15):
            self.expectedPayloadData.append([1, 1, 1, 0, 1, 0, 0, 1, 0, 0, 0, 0])
        self.expectedPayloadData.append([0, 0])
        for n in xrange(8):
            self.expectedPayloadData.append([1, 1, 1, 0, 1, 0, 0, 0, 1, 0, 0, 0])
        self.expectedPayloadData.append([])
        for n in xrange(4):
            self.expectedPayloadData.append([1, 1, 1, 0, 1, 0, 0, 0, 1, 0, 0, 0])
        self.expectedPayloadData.append([])
        for n in xrange(8):
            self.expectedPayloadData.append([1, 1, 1, 0, 1, 0, 0, 0, 0, 0, 1, 0])
        for n in xrange(15):
            self.expectedPayloadData.append([1, 1, 1, 0, 1, 0, 0, 0, 0, 0, 0, 1]) # 53
            
        return(0)
        
    def setUp(self):
        # load setup values
        self.loadBasicTestParameters()
        # load expected values for comparison
        self.loadExpectedData()
        
        # demodulate
        self.basebandData = demodIQFile(verbose = self.verbose,
                                        modulationType = self.protocol.modulation,
                                        iqSampleRate = self.samp_rate,
                                        basebandSampleRate = self.basebandSampleRate,
                                        centerFreq = self.center_freq,
                                        frequency = self.frequency,
                                        channelWidth = self.protocol.channelWidth,
                                        transitionWidth = self.protocol.transitionWidth,
                                        threshold = self.threshold,
                                        fskDeviation = self.protocol.fskDeviation,
                                        iqFileName = self.iqFileName,
                                        waveformFileName = self.waveformFileName)

        # split transmissions
        self.txList = buildTxList(basebandData = self.basebandData,
                                  basebandSampleRate =  self.basebandSampleRate,
                                  interTxTiming = self.timeBetweenTx_samp,
                                  glitchFilterCount = self.glitchFilterCount,
                                  verbose = self.verbose)    

        # decode
        (self.txList, self.decodeOutputString) = decodeAllTx(protocol = self.protocol, 
                                                             txList = self.txList, 
                                                             outputHex = self.outputHex,
                                                             timingError = self.timingError,
                                                             glitchFilterCount = self.glitchFilterCount,
                                                             verbose = self.verbose)
        
        # compute stats
        (self.bitProbList, self.idListCounter, self.value1List) = computeStats(txList = self.txList, protocol = self.protocol, showAllTx = self.showAllTx)
        # compute stat string
        (self.bitProbString, self.idStatString, self.valuesString) = buildStatStrings(self.bitProbList, self.idListCounter, self.value1List, self.outputHex)
        
        pass
        

    # compare transmissions to expected
    def test_compareTx(self):
        i = 0
        for tx in self.txList:
            #print tx.framingValid
            expectedbit = 1
            self.assertListEqual(tx.fullBasebandData, self.expectedPayloadData[i], "Bit comparison Error on TX#" + str(i))
            i += 1
        pass
        
    def test_framing(self):
        # build list of expected values
        expected = []
        for n in xrange(30):
            # preamble, header, framing, encoding, crc, txValid
            expected.append([True, True, True, True, True, True])    # 0-29
        expected.append([True, True, True, True, True, False])       # 30
        for n in xrange(8):
            expected.append([True, True, True, True, True, True])    # 31-38
        expected.append([False, False, False, True, True, False])    # 39
        for n in xrange(4):
            expected.append([True, True, True, True, True, True])    # 40-43
        expected.append([False, False, False, True, True, False])    # 44
        for n in xrange(23):
            expected.append([True, True, True, True, True, True])    # 45-64
        
        i = 0
        for tx in self.txList:
            #print str(i) + str(tx.preambleValid) + str(tx.headerValid) + str(tx.framingValid) + str(tx.encodingValid) + str(tx.crcValid) + str(tx.txValid)
            self.assertEqual(tx.preambleValid, expected[i][0], "Preamble Valid mismatch on TX#" + str(i))
            self.assertEqual(tx.headerValid, expected[i][1], "Header Valid mismatch on TX#" + str(i))
            self.assertEqual(tx.framingValid, expected[i][2], "Framing Valid mismatch on TX#" + str(i))
            self.assertEqual(tx.encodingValid, expected[i][3], "Encoding Valid mismatch on TX#" + str(i))
            self.assertEqual(tx.crcValid, expected[i][4], "CRC Valid mismatch on TX#" + str(i))
            self.assertEqual(tx.txValid, expected[i][5], "Transmission Valid mismatch on TX#" + str(i))
            i += 1
            
        pass
  
    def test_stats(self):
        import numpy as np

        # compute bit probabilities from the expected data, assuming good transmissions only
        sumArray = []
        goodTxCount = 0
        for payload in self.expectedPayloadData:
            if len(payload) == self.protocol.packetSize:
                goodTxCount += 1
                if sumArray == []:
                    sumArray = payload
                else:
                    sumArray = np.add(sumArray, payload)
        expectedBitProb = np.divide(sumArray, goodTxCount/100.0)

        # compare to values computed by code
        #print expectedBitProb
        #print self.bitProbList
        # number of probabilites should be identical
        self.assertEqual(len(self.bitProbList), len(expectedBitProb), "ERROR: expected length of bit probabilities list mismatch")
        for actual, expected in zip(self.bitProbList, expectedBitProb):
            self.assertAlmostEqual(actual, expected, msg = "ERROR: bit probablity mismatch " + str(actual) + " != " + str(expected))


        # compute id frequency from the expected data
        # create list of just the IDs in string form
        idList = []
        for payload in self.expectedPayloadData:
            idList.append(''.join(str(s) for s in payload[self.protocol.idAddrLow:self.protocol.idAddrHigh+1]))
        # now create dictionary of IDs and their counts
        expectedIdCountDict = {}
        for id in idList:
            if not id == "": # ignore the empty strings
                if id not in expectedIdCountDict:
                    expectedIdCountDict[id] = 1
                else:
                    expectedIdCountDict[id] += 1

        # now compare ID counts to expected values
        #print self.idListCounter
        #print expectedIdCountDict
        self.assertEqual(len(self.idListCounter), len(expectedIdCountDict), "ERROR: expected length of ID count list mismatch")
        for (idVal, idCount) in self.idListCounter.most_common():
            self.assertEqual(self.idListCounter[idVal], expectedIdCountDict[idVal], "ERROR: ID count mismatch")
        
        
        # build list of values from expected data
        expectedValue1List = []
        for payload in self.expectedPayloadData:
            if len(payload) == self.protocol.packetSize: # only considering good transmissions
                bitList = payload[self.protocol.val1AddrLow:self.protocol.val1AddrHigh]
                # convert bits to number
                value = 0
                for bit in bitList:
                    value = (value << 1) | bit
                # add to list
                expectedValue1List.append(int(value))
        
        # compare values
        #print self.value1List
        #print expectedValue1List
        self.assertEqual(len(self.value1List), len(expectedValue1List), "ERROR: expected length of Values 1 list mismatch")
        for actual, expected in zip(self.value1List, expectedValue1List):
            self.assertEqual(actual, expected, msg = "ERROR: Value mismatch")

        pass

if __name__ == '__main__':
    unittest.main()

